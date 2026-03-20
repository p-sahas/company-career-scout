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

        official_careers = await self._crawl_official_careers(company)
        results.extend(official_careers)

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

                    for card in cards[: self.max_results]:
                        text = card.get_text(strip=True)
                        if not text or len(text) < 10:
                            continue
                            
                        ignore_phrases = ["we did not find any result", "back to ikman", "no ads found", "0 ads"]
                        if any(p in text.lower() for p in ignore_phrases):
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

                    for item in job_items[: self.max_results]:
                        text = item.get_text(strip=True)
                        if not text or len(text) < 10:
                            continue
                            
                        ignore_phrases = ["no vacancies found", "0 results"]
                        if any(p in text.lower() for p in ignore_phrases):
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

    async def _crawl_official_careers(self, company: str) -> list[RawResult]:
        """Crawl official careers page and chase ATS redirects."""
        import os
        results = []
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_key:
            return results
            
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            
            # 1. Try to directly find a known ATS tenant first (much more reliable)
            ats_query = f'"{company}" Sri Lanka (site:myworkdaysite.com OR site:workday.com OR site:greenhouse.io OR site:lever.co OR site:smartrecruiters.com OR site:bamboohr.com)'
            response = client.search(
                query=ats_query,
                max_results=1,
                search_depth="advanced"
            )
            
            target_url = None
            if response.get("results"):
                target_url = response["results"][0]["url"]
                
            # 2. Fall back to finding the main Official Careers page
            if not target_url:
                response = client.search(
                    query=f'"{company}" official careers OR jobs Sri Lanka',
                    max_results=1,
                    search_depth="basic"
                )
                if response.get("results"):
                    target_url = response["results"][0]["url"]
            
            if not target_url:
                return results
            
            # Use Playwright to dig deeper
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    await page.goto(target_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
                    
                    ats_domains = [
                        "workday", "myworkdaysite.com", "greenhouse.io", "lever.co", 
                        "smartrecruiters", "bamboohr", "taleo", "icims", "ashbyhq", "workable"
                    ]
                    
                    # If we landed on a plain careers page, we still need to scout for "Explore" redirect buttons
                    if not any(ats in target_url.lower() for ats in ats_domains):
                        hrefs = await page.evaluate('''() => {
                            return Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText, href: a.href}));
                        }''')
                        
                        redirect_url = target_url
                        for link in hrefs:
                            href = link.get("href", "")
                            if not href: continue
                            href_lower = href.lower()
                            text_lower = link.get("text", "").lower()
                            
                            if any(ats in href_lower for ats in ats_domains):
                                if href_lower.startswith("http"):
                                    redirect_url = link["href"]
                                    break
                                    
                            if any(kw in text_lower for kw in ["explore", "view jobs", "openings", "search jobs"]):
                                if href_lower.startswith("http"):
                                    redirect_url = link["href"]
                        
                        # Go to the found ATS redirect
                        if redirect_url != target_url:
                            self.logger.info(f"Following careers ATS redirect from {target_url} to {redirect_url}")
                            try:
                                await page.goto(redirect_url, wait_until="networkidle", timeout=30000)
                                await page.wait_for_timeout(3000)
                                target_url = redirect_url
                            except Exception as e:
                                self.logger.warning(f"Failed to follow careers redirect to {redirect_url}: {e}")
                                
                    # Extract page text
                    text_content = await page.evaluate("document.body.innerText")
                    
                    if text_content and len(text_content) > 50:
                        results.append(
                            RawResult(
                                source_platform="topjobs",
                                source_url=target_url,
                                raw_text=self._safe_text(text_content),
                                reviewer_type="job_seeker",
                                metadata={
                                    "type": "job_listing",
                                    "source_site": "official_careers",
                                }
                            )
                        )
                    
                except Exception as e:
                    self.logger.warning(f"Careers page playwright error: {e}")
                finally:
                    await browser.close()
                    
        except Exception as e:
            self.logger.warning(f"Careers extraction error: {e}")
            
        return results
