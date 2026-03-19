"""
Facebook public pages crawler.
Extracts public page ratings, reviews, and reaction counts.
"""

import logging
import re
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)


class FacebookCrawler(BaseCrawler):
    """Crawls Facebook public pages for company reviews and ratings."""

    def __init__(self, max_results: int = 15):
        super().__init__(name="facebook", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search Facebook for public company page data.

        Uses Google to find Facebook pages, then extracts public info.

        Args:
            query: Search query (e.g. "WSO2 Sri Lanka").
            company: Normalized company name.

        Returns:
            List of RawResult objects from Facebook.
        """
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
                # Use Google to find Facebook company pages
                google_query = f'site:facebook.com "{company}" "Sri Lanka"'
                search_url = (
                    f"https://www.google.com/search?"
                    f"q={google_query.replace(' ', '+')}&num=10"
                )

                try:
                    response = await client.get(search_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Find Facebook page links
                        links = soup.find_all(
                            "a", href=re.compile(r"facebook\.com/")
                        )

                        seen_urls = set()
                        for link in links:
                            if len(results) >= self.max_results:
                                break

                            href = link.get("href", "")
                            url_match = re.search(
                                r"facebook\.com/[^/&\"'?]+", href
                            )
                            if not url_match:
                                continue

                            fb_url = f"https://www.{url_match.group(0)}"
                            if fb_url in seen_urls:
                                continue
                            seen_urls.add(fb_url)

                            # Get snippet text
                            parent = link.find_parent()
                            snippet = parent.get_text(strip=True) if parent else ""

                            # Extract rating if present
                            rating_match = re.search(
                                r'(\d\.?\d?)\s*(?:out of 5|stars?|rating)',
                                snippet,
                                re.I,
                            )
                            rating = (
                                float(rating_match.group(1))
                                if rating_match
                                else None
                            )

                            # Extract likes/followers
                            likes_match = re.search(
                                r'([\d,]+(?:\.\d+)?[KMkm]?)\s*(?:likes?|followers?)',
                                snippet,
                                re.I,
                            )

                            results.append(
                                RawResult(
                                    source_platform="facebook",
                                    source_url=fb_url,
                                    raw_text=self._safe_text(snippet),
                                    rating=rating,
                                    reviewer_type="customer",
                                    metadata={
                                        "type": "page_info",
                                        "likes": (
                                            likes_match.group(1)
                                            if likes_match
                                            else None
                                        ),
                                    },
                                )
                            )

                except Exception as e:
                    self.logger.warning(f"Google search for Facebook error: {e}")

        except Exception as e:
            self.logger.error(f"Facebook crawl error: {e}")

        self.logger.info(
            f"Facebook crawler found {len(results)} results for '{company}'"
        )
        return results
