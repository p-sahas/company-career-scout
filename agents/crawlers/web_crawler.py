"""
General web crawler (fallback).
Uses Brave Search API or direct Google search for SL-scoped results.
"""

import os
import logging
import re
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)


class WebCrawler(BaseCrawler):
    """Fallback web crawler using Brave Search API or Google."""

    def __init__(self, max_results: int = 10):
        super().__init__(name="web", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search the general web for SL company mentions.

        Args:
            query: Enriched search query with SL restriction.
            company: Normalized company name.

        Returns:
            List of RawResult objects from web search.
        """
        results = []

        # Try Brave Search API first
        brave_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        if brave_key:
            brave_results = await self._brave_search(query, brave_key)
            results.extend(brave_results)

        # Try SerpAPI if Brave didn't work
        if not results:
            serp_key = os.environ.get("SERPAPI_KEY")
            if serp_key:
                serp_results = await self._serpapi_search(query, serp_key)
                results.extend(serp_results)

        # Fallback to Google scraping
        if not results:
            google_results = await self._google_search(query, company)
            results.extend(google_results)

        self.logger.info(
            f"Web crawler found {len(results)} results for '{company}'"
        )
        return results[: self.max_results]

    async def _brave_search(
        self, query: str, api_key: str
    ) -> list[RawResult]:
        """Search using Brave Search API."""
        results = []

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": api_key,
                    },
                    params={
                        "q": query,
                        "count": self.max_results,
                        "country": "LK",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("web", {}).get("results", []):
                        results.append(
                            RawResult(
                                source_platform="web",
                                source_url=result.get("url", ""),
                                raw_text=self._safe_text(
                                    f"{result.get('title', '')}\n\n"
                                    f"{result.get('description', '')}"
                                ),
                                reviewer_type="general",
                                metadata={
                                    "type": "web_result",
                                    "search_engine": "brave",
                                    "title": result.get("title", ""),
                                },
                            )
                        )

        except Exception as e:
            self.logger.warning(f"Brave Search error: {e}")

        return results

    async def _serpapi_search(
        self, query: str, api_key: str
    ) -> list[RawResult]:
        """Search using SerpAPI."""
        results = []

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": api_key,
                        "gl": "lk",  # Sri Lanka
                        "num": self.max_results,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("organic_results", []):
                        results.append(
                            RawResult(
                                source_platform="web",
                                source_url=result.get("link", ""),
                                raw_text=self._safe_text(
                                    f"{result.get('title', '')}\n\n"
                                    f"{result.get('snippet', '')}"
                                ),
                                reviewer_type="general",
                                metadata={
                                    "type": "web_result",
                                    "search_engine": "serpapi",
                                    "title": result.get("title", ""),
                                    "position": result.get("position"),
                                },
                            )
                        )

        except Exception as e:
            self.logger.warning(f"SerpAPI error: {e}")

        return results

    async def _google_search(
        self, query: str, company: str
    ) -> list[RawResult]:
        """Fallback Google search scraping."""
        results = []

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                search_url = (
                    f"https://www.google.com/search?"
                    f"q={query.replace(' ', '+')}&num={self.max_results}"
                )

                response = await client.get(search_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    for div in soup.find_all("div", class_="g"):
                        link = div.find("a", href=True)
                        if not link:
                            continue

                        url = link["href"]
                        title_el = div.find("h3")
                        title = title_el.get_text(strip=True) if title_el else ""

                        snippet_el = div.find(
                            ["span", "div"],
                            class_=re.compile(r"st|snippet", re.I),
                        )
                        snippet = (
                            snippet_el.get_text(strip=True) if snippet_el else ""
                        )

                        # Only include if SL-related
                        from core.sl_validator import is_sri_lankan_result

                        combined = f"{title} {snippet} {url}"
                        if is_sri_lankan_result(combined, url):
                            results.append(
                                RawResult(
                                    source_platform="web",
                                    source_url=url,
                                    raw_text=self._safe_text(
                                        f"{title}\n\n{snippet}"
                                    ),
                                    reviewer_type="general",
                                    metadata={
                                        "type": "web_result",
                                        "search_engine": "google",
                                        "title": title,
                                    },
                                )
                            )

        except Exception as e:
            self.logger.warning(f"Google search error: {e}")

        return results
