"""
Analysis Agent — LLM-powered sentiment and theme extraction.
Classifies each raw result using the ModelRouter.
"""

import logging
from typing import Optional
from core.model_router import ModelRouter
from core.sl_validator import detect_crisis_signals
from agents.crawlers.base_crawler import RawResult

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    LLM-based analysis agent that classifies each result
    for sentiment, themes, severity, and crisis signals.
    """

    def __init__(self, model_router: ModelRouter):
        """
        Initialize the analysis agent.

        Args:
            model_router: Configured ModelRouter instance.
        """
        self.model_router = model_router
        self.logger = logging.getLogger("analysis_agent")

    async def analyze_results(
        self, results: list[dict]
    ) -> list[dict]:
        """
        Classify each result using the LLM.

        Args:
            results: List of raw result dicts (from crawlers).

        Returns:
            List of enriched result dicts with classification.
        """
        analyzed = []

        for i, result in enumerate(results):
            try:
                raw_text = result.get("raw_text", "")
                if not raw_text or len(raw_text.strip()) < 10:
                    continue

                self.logger.info(
                    f"Analyzing result {i+1}/{len(results)} "
                    f"from {result.get('source_platform', 'unknown')}"
                )

                # LLM classification
                classification = self.model_router.classify(raw_text)

                # Rule-based crisis detection (supplement LLM)
                crisis_flags = detect_crisis_signals(raw_text)

                # Merge classification into result
                enriched = {
                    **result,
                    **classification,
                    "crisis_flags": crisis_flags,
                }

                # If crisis detected, bump severity
                if crisis_flags and enriched.get("severity") not in (
                    "high",
                    "critical",
                ):
                    enriched["severity"] = "high"

                analyzed.append(enriched)

            except Exception as e:
                self.logger.warning(f"Error analyzing result {i}: {e}")
                # Keep the result but mark as unanalyzed
                analyzed.append(
                    {
                        **result,
                        "sentiment": "neutral",
                        "confidence": 0.0,
                        "reviewer_type": result.get("reviewer_type", "general"),
                        "themes": [],
                        "severity": "low",
                        "language_detected": "en",
                        "crisis_flags": [],
                        "analysis_error": str(e),
                    }
                )

        self.logger.info(
            f"Analysis complete: {len(analyzed)} results classified. "
            f"Tokens used: {self.model_router.total_tokens_used}"
        )

        return analyzed

    async def generate_summary(self, analyzed_results: list[dict]) -> dict:
        """
        Generate an aggregated summary from all analyzed results.

        Args:
            analyzed_results: List of classified result dicts.

        Returns:
            Summary dict with employee/customer/press views, pros, cons.
        """
        try:
            summary = self.model_router.summarize(analyzed_results)

            # Supplement with rule-based crisis flags
            all_crisis = []
            for r in analyzed_results:
                all_crisis.extend(r.get("crisis_flags", []))

            if all_crisis:
                existing_flags = summary.get("crisis_flags", [])
                combined_flags = list(set(existing_flags + all_crisis))
                summary["crisis_flags"] = combined_flags

            return summary

        except Exception as e:
            self.logger.error(f"Summary generation error: {e}")
            return {
                "what_employees_say": "Summary generation failed.",
                "what_customers_say": "Summary generation failed.",
                "what_press_says": "Summary generation failed.",
                "top_5_pros": [],
                "top_5_cons": [],
                "crisis_flags": [],
                "recommendation": "Unable to generate recommendation.",
                "overall_score": 50,
                "error": str(e),
            }
