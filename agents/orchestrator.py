"""
LangGraph Orchestrator — StateGraph definition.
Coordinates the full pipeline: Input → Crawl → Filter → Analyze → Report.
"""

import asyncio
import logging
from typing import TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from core.sl_validator import normalize_company_name, enrich_query, is_sri_lankan_result
from core.model_router import ModelRouter
from core.cache import CacheManager
from core.deduplicator import deduplicate_results
from agents.crawlers.reddit_crawler import RedditCrawler
from agents.crawlers.google_maps_crawler import GoogleMapsCrawler
from agents.crawlers.glassdoor_crawler import GlassdoorCrawler
from agents.crawlers.topjobs_crawler import TopJobsCrawler
from agents.crawlers.linkedin_crawler import LinkedInCrawler
from agents.crawlers.facebook_crawler import FacebookCrawler
from agents.crawlers.news_crawler import NewsCrawler
from agents.crawlers.web_crawler import WebCrawler
from agents.analysis_agent import AnalysisAgent
from agents.report_builder import ReportBuilder

logger = logging.getLogger(__name__)


# --- State Schema ---

class ScoutState(TypedDict):
    """State managed by the LangGraph orchestrator."""
    company_raw: str
    company: str
    enriched_queries: dict  # platform -> query string
    raw_results: list       # all raw results from crawlers
    validated_results: list  # after SL validation
    analyzed_results: list   # after LLM analysis
    summary: dict            # aggregated summary
    report: dict             # final report
    model_router: object     # ModelRouter instance
    cache_manager: object    # CacheManager instance
    status: str              # current pipeline status
    errors: list             # accumulated errors
    cache_hits: dict         # source -> bool (whether cache was used)


# --- Node Functions ---

def input_validator(state: ScoutState) -> dict:
    """
    NODE 1: Validate and normalize the company name input.
    Enrich queries for each platform.
    """
    company_raw = state["company_raw"]

    # Normalize
    company = normalize_company_name(company_raw)

    # Build enriched queries per platform
    platforms = [
        "reddit", "google_maps", "glassdoor", "topjobs",
        "linkedin", "facebook", "news", "web",
    ]
    enriched = {p: enrich_query(company, p) for p in platforms}

    logger.info(f"Input validated: '{company_raw}' → '{company}'")

    return {
        "company": company,
        "enriched_queries": enriched,
        "status": "input_validated",
        "errors": [],
        "cache_hits": {},
    }


async def parallel_crawlers(state: ScoutState) -> dict:
    """
    NODE 2: Run all crawlers in parallel (async).
    Uses cache when available.
    """
    company = state["company"]
    queries = state["enriched_queries"]
    cache: CacheManager = state["cache_manager"]
    all_results = []
    cache_hits = {}

    # Define crawlers with their platform keys
    crawlers = [
        ("reddit", RedditCrawler()),
        ("google_maps", GoogleMapsCrawler()),
        ("glassdoor", GlassdoorCrawler()),
        ("topjobs", TopJobsCrawler()),
        ("linkedin", LinkedInCrawler()),
        ("facebook", FacebookCrawler()),
        ("news", NewsCrawler()),
        ("web", WebCrawler()),
    ]

    async def run_crawler(platform: str, crawler, query: str):
        """Run a single crawler, checking cache first."""
        # Check cache
        cached = cache.get(company, platform)
        if cached is not None:
            cache_age = cache.get_cache_age_display(company, platform)
            logger.info(
                f"[{platform}] Using cached data ({cache_age})"
            )
            cache_hits[platform] = True
            return cached

        cache_hits[platform] = False
        try:
            logger.info(f"[{platform}] Starting crawl...")
            results = await crawler.crawl(query, company)
            result_dicts = [
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in results
            ]
            # Cache results
            if result_dicts:
                cache.set(company, platform, result_dicts)
            logger.info(
                f"[{platform}] Crawl complete: {len(result_dicts)} results"
            )
            return result_dicts
        except Exception as e:
            logger.error(f"[{platform}] Crawl failed: {e}")
            return []

    # Run all crawlers concurrently
    tasks = [
        run_crawler(platform, crawler, queries.get(platform, company))
        for platform, crawler in crawlers
    ]
    results_by_platform = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results
    errors = []
    for (platform, _), result in zip(crawlers, results_by_platform):
        if isinstance(result, Exception):
            errors.append(f"{platform}: {str(result)}")
        elif isinstance(result, list):
            all_results.extend(result)

    logger.info(
        f"Total raw results: {len(all_results)} "
        f"(cache hits: {sum(1 for v in cache_hits.values() if v)}/"
        f"{len(cache_hits)})"
    )

    return {
        "raw_results": all_results,
        "status": "crawling_complete",
        "errors": errors,
        "cache_hits": cache_hits,
    }


def sl_validation_filter(state: ScoutState) -> dict:
    """
    NODE 3: Filter results through Sri Lanka validation.
    Discard any result that fails the SL check.
    """
    raw_results = state.get("raw_results", [])
    validated = []
    discarded = 0
    company = state.get("company", "")

    from core.sl_validator import mentions_company, COMPANY_ALIASES

    for result in raw_results:
        text = result.get("raw_text", "")
        url = result.get("source_url", "")
        platform = result.get("source_platform", "")

        # Strict relevance check: must mention company OR be from native SL job board
        if not mentions_company(text, company) and not url.lower().endswith(tuple(COMPANY_ALIASES.keys())):
            # Wait, URL might not have alias. Just check text.
            if not mentions_company(text, company) and not mentions_company(url, company):
                discarded += 1
                logger.debug(f"Discarded irrelevant result from {platform}: {url[:50]}")
                continue

        # SL-native platforms always pass geo-check
        if platform in ("topjobs",):
            validated.append(result)
            continue

        # Run validation
        if is_sri_lankan_result(text, url):
            validated.append(result)
        else:
            discarded += 1
            logger.debug(
                f"Discarded non-SL result from {platform}: {url[:50]}"
            )

    # Deduplication
    before_dedup = len(validated)
    validated = deduplicate_results(validated)
    dedup_removed = before_dedup - len(validated)

    logger.info(
        f"SL validation: {len(validated)} passed, {discarded} discarded, "
        f"{dedup_removed} duplicates removed"
    )

    return {
        "validated_results": validated,
        "status": "validation_complete",
    }


async def analysis_node(state: ScoutState) -> dict:
    """
    NODE 4: Run LLM analysis on validated results.
    """
    validated = state.get("validated_results", [])
    model_router: ModelRouter = state["model_router"]
    agent = AnalysisAgent(model_router)

    # Analyze all results
    analyzed = await agent.analyze_results(validated)

    # Generate summary
    summary = await agent.generate_summary(analyzed)

    logger.info(
        f"Analysis complete: {len(analyzed)} results analyzed, "
        f"tokens used: {model_router.total_tokens_used}"
    )

    return {
        "analyzed_results": analyzed,
        "summary": summary,
        "status": "analysis_complete",
    }


def report_node(state: ScoutState) -> dict:
    """
    NODE 5: Build the final structured report.
    """
    company = state["company"]
    analyzed = state.get("analyzed_results", [])
    summary = state.get("summary", {})
    model_router: ModelRouter = state["model_router"]
    cache: CacheManager = state["cache_manager"]

    builder = ReportBuilder()
    report = builder.build_report(
        company=company,
        analyzed_results=analyzed,
        summary=summary,
        model_used=model_router.get_display_name(),
    )

    # Add cache info to report
    report["cache_hits"] = state.get("cache_hits", {})

    # Cache the full report
    cache.set_analysis(company, report, model_router.get_display_name())

    # Log token usage
    usage = model_router.get_usage_stats()
    cache.log_token_usage(
        company=company,
        provider=usage["provider"],
        model=usage["model"],
        tokens_used=usage["total_tokens"],
        calls_made=usage["total_calls"],
    )

    logger.info(
        f"Report built for '{company}': score={report.get('overall_score', 'N/A')}"
    )

    return {
        "report": report,
        "status": "complete",
    }


# --- Graph Builder ---

def build_scout_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the Company Career Scout pipeline.

    Returns:
        Compiled StateGraph.
    """
    graph = StateGraph(ScoutState)

    # Add nodes
    graph.add_node("input_validator", input_validator)
    graph.add_node("parallel_crawlers", parallel_crawlers)
    graph.add_node("sl_validation_filter", sl_validation_filter)
    graph.add_node("analysis", analysis_node)
    graph.add_node("report_builder", report_node)

    # Add edges (linear pipeline)
    graph.add_edge(START, "input_validator")
    graph.add_edge("input_validator", "parallel_crawlers")
    graph.add_edge("parallel_crawlers", "sl_validation_filter")
    graph.add_edge("sl_validation_filter", "analysis")
    graph.add_edge("analysis", "report_builder")
    graph.add_edge("report_builder", END)

    return graph.compile()


async def run_scout(
    company_name: str,
    model_router: ModelRouter,
    cache_manager: CacheManager = None,
) -> dict:
    """
    Run the complete Company Career Scout pipeline.

    Args:
        company_name: Raw company name input.
        model_router: Configured ModelRouter instance.
        cache_manager: Optional CacheManager (creates default if None).

    Returns:
        Final report dict.
    """
    if cache_manager is None:
        cache_manager = CacheManager()

    graph = build_scout_graph()

    initial_state = {
        "company_raw": company_name,
        "company": "",
        "enriched_queries": {},
        "raw_results": [],
        "validated_results": [],
        "analyzed_results": [],
        "summary": {},
        "report": {},
        "model_router": model_router,
        "cache_manager": cache_manager,
        "status": "starting",
        "errors": [],
        "cache_hits": {},
    }

    # Run the graph
    result = await graph.ainvoke(initial_state)
    return result.get("report", {})
