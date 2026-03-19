"""
LinkedIn crawler for public company information.
Extracts follower count, employee count, and recent posts.
"""

import logging
import re
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)


class LinkedInCrawler(BaseCrawler):
    """Crawls LinkedIn public search for company info (no auth needed for basic data)."""

    def __init__(self, max_results: int = 10):
        super().__init__(name="linkedin", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search LinkedIn for public company information.

        Uses Google search to find LinkedIn company pages (avoids LinkedIn auth).

        Args:
            query: Company name.
            company: Normalized company name.

        Returns:
            List of RawResult objects from LinkedIn.
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
                # Use Google to find LinkedIn company page
                google_query = (
                    f'site:linkedin.com/company "{company}" "Sri Lanka"'
                )
                search_url = (
                    f"https://www.google.com/search?q={google_query.replace(' ', '+')}"
                    f"&num=5"
                )

                try:
                    response = await client.get(search_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Extract LinkedIn URLs from Google results
                        links = soup.find_all("a", href=re.compile(r"linkedin\.com/company"))

                        for link in links[: self.max_results]:
                            href = link.get("href", "")
                            # Extract actual URL from Google redirect
                            url_match = re.search(
                                r"linkedin\.com/company/[^/&\"']+", href
                            )
                            if url_match:
                                linkedin_url = f"https://www.{url_match.group(0)}"

                                # Get the snippet text from Google
                                parent = link.find_parent()
                                snippet = parent.get_text(strip=True) if parent else ""

                                # Extract metrics from snippet
                                follower_match = re.search(
                                    r'([\d,]+)\s*followers?', snippet, re.I
                                )
                                employee_match = re.search(
                                    r'([\d,]+(?:\s*[-–]\s*[\d,]+)?)\s*employees?',
                                    snippet,
                                    re.I,
                                )

                                results.append(
                                    RawResult(
                                        source_platform="linkedin",
                                        source_url=linkedin_url,
                                        raw_text=self._safe_text(snippet),
                                        reviewer_type="general",
                                        metadata={
                                            "type": "company_profile",
                                            "followers": (
                                                follower_match.group(1)
                                                if follower_match
                                                else None
                                            ),
                                            "employees": (
                                                employee_match.group(1)
                                                if employee_match
                                                else None
                                            ),
                                        },
                                    )
                                )

                except Exception as e:
                    self.logger.warning(f"Google search for LinkedIn error: {e}")

                # Also try direct LinkedIn search (public, no auth)
                try:
                    li_search_url = (
                        f"https://www.linkedin.com/search/results/companies/"
                        f"?keywords={company.replace(' ', '%20')}"
                        f"&geoUrn=%5B%22108065294%22%5D"  # Sri Lanka geo ID
                    )
                    response = await client.get(li_search_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        # Extract any publicly visible company info
                        company_cards = soup.find_all(
                            "div", class_=re.compile(r"entity-result", re.I)
                        )
                        for card in company_cards[: self.max_results - len(results)]:
                            text = card.get_text(strip=True)
                            if text and len(text) > 20:
                                results.append(
                                    RawResult(
                                        source_platform="linkedin",
                                        source_url=li_search_url,
                                        raw_text=self._safe_text(text),
                                        reviewer_type="general",
                                        metadata={
                                            "type": "search_result",
                                        },
                                    )
                                )
                except Exception as e:
                    self.logger.warning(f"LinkedIn direct search error: {e}")

        except Exception as e:
            self.logger.error(f"LinkedIn crawl error: {e}")

        self.logger.info(
            f"LinkedIn crawler found {len(results)} results for '{company}'"
        )
        return results
