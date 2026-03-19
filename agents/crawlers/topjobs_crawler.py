"""
Sri Lankan job boards crawler.
Scrapes topjobs.lk, ikman.lk/en/jobs, and jobsnet.lk.
These are SL-native sites, so no geo-filter is needed.
"""

import logging
import re
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)


class TopJobsCrawler(BaseCrawler):
    """Crawls Sri Lankan job boards for company job listings."""

    def __init__(self, max_results: int = 30):
        super().__init__(name="topjobs", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search SL job boards for company listings.

        Args:
            query: Company name (no geo-restriction needed for .lk sites).
            company: Normalized company name.

        Returns:
            List of RawResult objects from SL job boards.
        """
        results = []

        # Crawl each job board
        topjobs_results = await self._crawl_topjobs(company)
        results.extend(topjobs_results)

        ikman_results = await self._crawl_ikman(company)
        results.extend(ikman_results)

        jobsnet_results = await self._crawl_jobsnet(company)
        results.extend(jobsnet_results)

        self.logger.info(
            f"SL Job Boards crawler found {len(results)} results for '{company}'"
        )
        return results[: self.max_results]

    async def _crawl_topjobs(self, company: str) -> list[RawResult]:
        """Crawl topjobs.lk for job listings."""
        results = []

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True
            ) as client:
                search_url = f"https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=ALL&src=hp"
                response = await client.get(search_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Search for company mentions in job listings
                    job_elements = soup.find_all(
                        string=re.compile(re.escape(company), re.I)
                    )

                    for element in job_elements[: self.max_results // 3]:
                        parent = element.find_parent()
                        if parent:
                            listing_text = parent.get_text(strip=True)
                            # Try to find salary info
                            salary_match = re.search(
                                r'(?:LKR|Rs\.?)\s*([\d,]+(?:\s*[-–]\s*[\d,]+)?)',
                                listing_text,
                                re.I,
                            )

                            results.append(
                                RawResult(
                                    source_platform="topjobs",
                                    source_url="https://www.topjobs.lk",
                                    raw_text=self._safe_text(listing_text),
                                    reviewer_type="job_seeker",
                                    metadata={
                                        "type": "job_listing",
                                        "source_site": "topjobs.lk",
                                        "salary_info": (
                                            salary_match.group(0) if salary_match else None
                                        ),
                                    },
                                )
                            )

        except Exception as e:
            self.logger.warning(f"TopJobs crawl error: {e}")

        return results

    async def _crawl_ikman(self, company: str) -> list[RawResult]:
        """Crawl ikman.lk for job listings."""
        results = []

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True
            ) as client:
                search_url = (
                    f"https://ikman.lk/en/ads/sri-lanka/jobs?"
                    f"query={company.replace(' ', '+')}"
                )
                response = await client.get(search_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find job listing cards
                    cards = soup.find_all(
                        ["li", "div", "a"],
                        class_=re.compile(r"card|listing|item|ad", re.I),
                    )

                    for card in cards[: self.max_results // 3]:
                        text = card.get_text(strip=True)
                        if not text or len(text) < 10:
                            continue

                        link = card.find("a", href=True)
                        url = (
                            f"https://ikman.lk{link['href']}"
                            if link
                            else "https://ikman.lk"
                        )

                        # Extract salary if present
                        salary_match = re.search(
                            r'(?:LKR|Rs\.?)\s*([\d,]+(?:\s*[-–]\s*[\d,]+)?)',
                            text,
                            re.I,
                        )

                        results.append(
                            RawResult(
                                source_platform="topjobs",
                                source_url=url,
                                raw_text=self._safe_text(text),
                                reviewer_type="job_seeker",
                                metadata={
                                    "type": "job_listing",
                                    "source_site": "ikman.lk",
                                    "salary_info": (
                                        salary_match.group(0) if salary_match else None
                                    ),
                                },
                            )
                        )

        except Exception as e:
            self.logger.warning(f"ikman.lk crawl error: {e}")

        return results

    async def _crawl_jobsnet(self, company: str) -> list[RawResult]:
        """Crawl jobsnet.lk for job listings."""
        results = []

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True
            ) as client:
                search_url = (
                    f"https://www.jobsnet.lk/job-vacancies.php?"
                    f"search={company.replace(' ', '+')}"
                )
                response = await client.get(search_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find job listings
                    job_items = soup.find_all(
                        ["div", "tr", "li"],
                        class_=re.compile(r"job|listing|vacancy", re.I),
                    )

                    for item in job_items[: self.max_results // 3]:
                        text = item.get_text(strip=True)
                        if not text or len(text) < 10:
                            continue

                        results.append(
                            RawResult(
                                source_platform="topjobs",
                                source_url="https://www.jobsnet.lk",
                                raw_text=self._safe_text(text),
                                reviewer_type="job_seeker",
                                metadata={
                                    "type": "job_listing",
                                    "source_site": "jobsnet.lk",
                                },
                            )
                        )

        except Exception as e:
            self.logger.warning(f"jobsnet.lk crawl error: {e}")

        return results
