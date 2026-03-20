"""
Report Builder — Assembles source-sorted structured report.
Organizes analyzed results by source platform.
"""

import logging
from datetime import datetime
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Builds the final structured report organized by source.
    """

    def __init__(self):
        self.logger = logging.getLogger("report_builder")

    def build_report(
        self,
        company: str,
        analyzed_results: list[dict],
        summary: dict,
        model_used: str,
    ) -> dict:
        """
        Build the complete source-sorted report.

        Args:
            company: Company name.
            analyzed_results: List of analyzed result dicts.
            summary: Aggregated summary dict from analysis agent.
            model_used: Name of the LLM model used.

        Returns:
            Complete report dict matching the spec schema.
        """
        # Group results by source
        by_source = defaultdict(list)
        for result in analyzed_results:
            platform = result.get("source_platform", "web")
            by_source[platform].append(result)

        # Build per-source sections
        source_reports = {}

        # Reddit
        if "reddit" in by_source:
            source_reports["reddit"] = self._build_reddit_section(
                by_source["reddit"]
            )

        # Google Maps
        if "google_maps" in by_source:
            source_reports["google_maps"] = self._build_google_maps_section(
                by_source["google_maps"]
            )

        # Glassdoor
        if "glassdoor" in by_source:
            source_reports["glassdoor"] = self._build_glassdoor_section(
                by_source["glassdoor"]
            )

        # TopJobs / Ikman
        if "topjobs" in by_source:
            source_reports["topjobs_ikman"] = self._build_topjobs_section(
                by_source["topjobs"]
            )

        # LinkedIn
        if "linkedin" in by_source:
            source_reports["linkedin"] = self._build_linkedin_section(
                by_source["linkedin"]
            )

        # Facebook
        if "facebook" in by_source:
            source_reports["facebook"] = self._build_facebook_section(
                by_source["facebook"]
            )

        # News
        if "news" in by_source:
            source_reports["sl_news"] = self._build_news_section(
                by_source["news"]
            )

        # General Web
        if "web" in by_source:
            source_reports["web_general"] = self._build_web_section(
                by_source["web"]
            )

        # Calculate overall score
        overall_score = summary.get("overall_score", self._calculate_score(analyzed_results))

        report = {
            "company": company,
            "generated_at": datetime.now().isoformat(),
            "model_used": model_used,
            "overall_score": overall_score,
            "total_results": len(analyzed_results),
            "analyzed_results": analyzed_results,
            "by_source": source_reports,
            "aggregated_summary": {
                "what_employees_say": summary.get(
                    "what_employees_say", "No employee data available."
                ),
                "what_customers_say": summary.get(
                    "what_customers_say", "No customer data available."
                ),
                "what_press_says": summary.get(
                    "what_press_says", "No press data available."
                ),
                "top_5_pros": summary.get("top_5_pros", []),
                "top_5_cons": summary.get("top_5_cons", []),
                "crisis_flags": summary.get("crisis_flags", []),
                "recommendation": summary.get(
                    "recommendation", "Insufficient data."
                ),
            },
        }

        self.logger.info(
            f"Report built for '{company}': {len(analyzed_results)} results "
            f"across {len(source_reports)} sources, score={overall_score}"
        )

        return report

    def _sentiment_breakdown(self, results: list) -> dict:
        """Count sentiment distribution."""
        counter = Counter(r.get("sentiment", "neutral") for r in results)
        return {
            "positive": counter.get("positive", 0),
            "negative": counter.get("negative", 0),
            "neutral": counter.get("neutral", 0),
        }

    def _top_themes(self, results: list, limit: int = 5) -> list:
        """Get most common themes."""
        all_themes = []
        for r in results:
            all_themes.extend(r.get("themes", []))
        return [t for t, _ in Counter(all_themes).most_common(limit)]

    def _sample_quotes(self, results: list, limit: int = 3) -> list:
        """Get representative sample quotes."""
        quotes = []
        for r in sorted(
            results,
            key=lambda x: x.get("confidence", 0),
            reverse=True,
        ):
            text = r.get("raw_text", "")
            if text and len(text) > 20:
                # Truncate for readability
                quote = text[:200] + "..." if len(text) > 200 else text
                quotes.append(quote)
                if len(quotes) >= limit:
                    break
        return quotes

    def _get_urls(self, results: list) -> list:
        """Get unique source URLs."""
        urls = []
        seen = set()
        for r in results:
            url = r.get("source_url", "")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    def _build_reddit_section(self, results: list) -> dict:
        """Build Reddit source section."""
        subreddits = set()
        for r in results:
            sub = r.get("metadata", {}).get("subreddit", "")
            if sub:
                subreddits.add(f"r/{sub}")

        return {
            "platform": "Reddit",
            "subreddits_searched": sorted(subreddits),
            "result_count": len(results),
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _build_google_maps_section(self, results: list) -> dict:
        """Build Google Maps source section."""
        ratings = [
            r.get("rating") for r in results if r.get("rating") is not None
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Get review count from metadata
        review_count = 0
        for r in results:
            rc = r.get("metadata", {}).get("review_count")
            if rc:
                review_count = max(review_count, rc)

        return {
            "platform": "Google Maps",
            "result_count": len(results),
            "avg_rating": round(avg_rating, 1) if avg_rating else None,
            "review_count": review_count,
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _build_glassdoor_section(self, results: list) -> dict:
        """Build Glassdoor/Indeed source section."""
        ratings = [
            r.get("rating") for r in results if r.get("rating") is not None
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Collect pros and cons
        pros = []
        cons = []
        roles = set()
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("pros"):
                pros.append(meta["pros"])
            if meta.get("cons"):
                cons.append(meta["cons"])
            role = meta.get("reviewer_role")
            if role:
                roles.add(role)

        return {
            "platform": "Glassdoor / Indeed",
            "result_count": len(results),
            "employee_count": len(results),
            "avg_rating": round(avg_rating, 1) if avg_rating else None,
            "top_pros": pros[:5],
            "top_cons": cons[:5],
            "roles_represented": sorted(roles),
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "urls": self._get_urls(results),
        }

    def _build_topjobs_section(self, results: list) -> dict:
        """Build TopJobs/Ikman/JobsNet section."""
        # Extract salary ranges
        salary_ranges = []
        for r in results:
            salary = r.get("metadata", {}).get("salary_info")
            if salary:
                salary_ranges.append(salary)

        # Determine hiring trend based on count
        job_count = len(results)
        if job_count >= 10:
            trend = "growing"
        elif job_count >= 3:
            trend = "stable"
        elif job_count >= 1:
            trend = "shrinking"
        else:
            trend = "none"

        return {
            "platform": "SL Job Boards (TopJobs, Ikman, JobsNet)",
            "active_job_count": job_count,
            "salary_range_lkr": salary_ranges[0] if salary_ranges else None,
            "all_salary_info": salary_ranges,
            "hiring_trend": trend,
            "result_count": len(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _build_linkedin_section(self, results: list) -> dict:
        """Build LinkedIn section."""
        followers = None
        employees = None
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("followers"):
                followers = meta["followers"]
            if meta.get("employees"):
                employees = meta["employees"]

        return {
            "platform": "LinkedIn",
            "result_count": len(results),
            "followers": followers,
            "employees": employees,
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _build_facebook_section(self, results: list) -> dict:
        """Build Facebook section."""
        ratings = [
            r.get("rating") for r in results if r.get("rating") is not None
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        likes = None
        for r in results:
            l = r.get("metadata", {}).get("likes")
            if l:
                likes = l

        return {
            "platform": "Facebook",
            "result_count": len(results),
            "avg_rating": round(avg_rating, 1) if avg_rating else None,
            "page_likes": likes,
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _build_news_section(self, results: list) -> dict:
        """Build SL News section."""
        articles = []
        for r in results:
            meta = r.get("metadata", {})
            articles.append(
                {
                    "headline": meta.get("headline", r.get("raw_text", "")[:100]),
                    "source": meta.get("source_site", "unknown"),
                    "date": r.get("date"),
                    "sentiment": r.get("sentiment", "neutral"),
                    "url": r.get("source_url", ""),
                }
            )

        return {
            "platform": "SL News",
            "result_count": len(results),
            "articles": articles,
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "urls": self._get_urls(results),
        }

    def _build_web_section(self, results: list) -> dict:
        """Build general web section."""
        return {
            "platform": "General Web",
            "result_count": len(results),
            "sentiment_breakdown": self._sentiment_breakdown(results),
            "top_themes": self._top_themes(results),
            "sample_quotes": self._sample_quotes(results),
            "urls": self._get_urls(results),
        }

    def _calculate_score(self, results: list) -> int:
        """Calculate overall score (0–100) from sentiment distribution."""
        if not results:
            return 50

        sentiments = [r.get("sentiment", "neutral") for r in results]
        total = len(sentiments)
        positive = sentiments.count("positive")
        negative = sentiments.count("negative")

        # Base score: positive ratio * 100
        score = int((positive / total) * 100) if total > 0 else 50

        # Penalty for crisis flags
        crisis_count = sum(
            1 for r in results if r.get("crisis_flags")
        )
        score -= crisis_count * 5

        # Penalty for high negative ratio
        if total > 0 and (negative / total) > 0.5:
            score -= 10

        return max(0, min(100, score))
