"""
Sri Lankan news crawler.
Searches SL news sites and Google News for company mentions.
"""

import logging
import re
from datetime import datetime, timedelta
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)

# Sri Lankan news sources
SL_NEWS_SITES = [
    "dailymirror.lk",
    "sundaytimes.lk",
    "lankabusinessonline.com",
    "adaderana.lk",
    "colombogazette.com",
    "ft.lk",
    "island.lk",
    "newsfirst.lk",
    "economynext.com",
]


class NewsCrawler(BaseCrawler):
    """Crawls Sri Lankan news sources for company mentions."""

    def __init__(self, max_results: int = 20):
        super().__init__(name="news", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search SL news sources for company articles.

        Args:
            query: Enriched search query (includes site:.lk).
            company: Normalized company name.

        Returns:
            List of RawResult objects from news sources.
        """
        results = []

        # Use Google News search with SL site restriction
        google_news_results = await self._search_google_news(company)
        results.extend(google_news_results)

        # Also try direct scraping of major SL news sites
        for site in SL_NEWS_SITES[:5]:  # Limit to top 5 sites
            if len(results) >= self.max_results:
                break
            site_results = await self._search_news_site(site, company)
            results.extend(site_results)

        self.logger.info(
            f"News crawler found {len(results)} results for '{company}'"
        )
        return results[: self.max_results]

    async def _search_google_news(self, company: str) -> list[RawResult]:
        """Search Google News for SL company articles."""
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
                # Build query with SL news site restriction
                sites_or = " OR ".join([f"site:{s}" for s in SL_NEWS_SITES[:5]])
                query = f'"{company}" ({sites_or})'
                search_url = (
                    f"https://www.google.com/search?"
                    f"q={query.replace(' ', '+')}&tbm=nws&tbs=qdr:y"
                )  # qdr:y = past year

                try:
                    response = await client.get(search_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Extract news article snippets
                        articles = soup.find_all(
                            "div", class_=re.compile(r"result|article|news", re.I)
                        )

                        for article in articles[: self.max_results]:
                            try:
                                # Get headline
                                headline_el = article.find(["h3", "h2", "a"])
                                headline = (
                                    headline_el.get_text(strip=True)
                                    if headline_el
                                    else ""
                                )

                                # Get snippet
                                snippet_el = article.find(
                                    ["p", "span", "div"],
                                    class_=re.compile(r"snippet|desc|text", re.I),
                                )
                                snippet = (
                                    snippet_el.get_text(strip=True)
                                    if snippet_el
                                    else article.get_text(strip=True)
                                )

                                # Get URL
                                link = article.find("a", href=True)
                                url = link["href"] if link else ""

                                # Get date
                                date_el = article.find(
                                    ["time", "span"],
                                    class_=re.compile(r"date|time|ago", re.I),
                                )
                                date_str = (
                                    date_el.get_text(strip=True)
                                    if date_el
                                    else None
                                )

                                # Determine source
                                source_site = "unknown"
                                for site in SL_NEWS_SITES:
                                    if site in url:
                                        source_site = site
                                        break

                                if headline or snippet:
                                    article_text = (
                                        f"{headline}\n\n{snippet}"
                                        if headline
                                        else snippet
                                    )
                                    results.append(
                                        RawResult(
                                            source_platform="news",
                                            source_url=url,
                                            raw_text=self._safe_text(article_text),
                                            date=date_str,
                                            reviewer_type="press",
                                            metadata={
                                                "type": "news_article",
                                                "headline": headline,
                                                "source_site": source_site,
                                            },
                                        )
                                    )
                            except Exception:
                                continue

                except Exception as e:
                    self.logger.warning(f"Google News search error: {e}")

        except Exception as e:
            self.logger.warning(f"Google News crawl error: {e}")

        return results

    async def _search_news_site(
        self, site: str, company: str
    ) -> list[RawResult]:
        """Search a specific SL news site for company articles."""
        results = []

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                # Use Google to search within the specific site
                search_url = (
                    f"https://www.google.com/search?"
                    f'q=site:{site}+"{company}"&num=5&tbs=qdr:y'
                )

                try:
                    response = await client.get(search_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")

                        for link in soup.find_all("a", href=True):
                            if site in link["href"]:
                                headline = link.get_text(strip=True)
                                if headline and len(headline) > 10:
                                    results.append(
                                        RawResult(
                                            source_platform="news",
                                            source_url=link["href"],
                                            raw_text=self._safe_text(headline),
                                            reviewer_type="press",
                                            metadata={
                                                "type": "news_article",
                                                "headline": headline,
                                                "source_site": site,
                                            },
                                        )
                                    )

                except Exception as e:
                    self.logger.warning(f"Site search error for {site}: {e}")

        except Exception as e:
            self.logger.warning(f"News site crawl error for {site}: {e}")

        return results
