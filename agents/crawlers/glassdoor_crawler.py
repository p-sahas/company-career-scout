"""
Glassdoor / Indeed crawler.
Extracts employee reviews with SL country filter.
"""

import logging
import re
from typing import Optional
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)


class GlassdoorCrawler(BaseCrawler):
    """Crawls Glassdoor and Indeed for Sri Lankan employee reviews."""

    def __init__(self, max_results: int = 40):
        super().__init__(name="glassdoor", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search Glassdoor/Indeed for employee reviews.

        Args:
            query: Company name.
            company: Normalized company name.

        Returns:
            List of RawResult objects from Glassdoor/Indeed.
        """
        results = []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.warning("Playwright not installed. Skipping Glassdoor crawler.")
            return results

        # Try Glassdoor
        glassdoor_results = await self._crawl_glassdoor(company)
        results.extend(glassdoor_results)

        # Try Indeed if we need more
        if len(results) < self.max_results:
            indeed_results = await self._crawl_indeed(company)
            results.extend(indeed_results)

        self.logger.info(
            f"Glassdoor/Indeed crawler found {len(results)} results for '{company}'"
        )
        return results[: self.max_results]

    async def _crawl_glassdoor(self, company: str) -> list[RawResult]:
        """Crawl Glassdoor for reviews."""
        results = []

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Search Glassdoor
                company_slug = company.lower().replace(" ", "-")
                search_url = f"https://www.glassdoor.com/Search/results.htm?keyword={company.replace(' ', '+')}&locT=N&locId=199"
                # locId=199 is Sri Lanka

                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)

                    content = await page.content()

                    # Extract overall rating
                    rating_match = re.search(
                        r'class="[^"]*rating[^"]*"[^>]*>(\d\.?\d?)', content, re.I
                    )
                    overall_rating = (
                        float(rating_match.group(1)) if rating_match else None
                    )

                    # Try to find and navigate to reviews page
                    review_links = page.locator('a[href*="Reviews"]')
                    if await review_links.count() > 0:
                        await review_links.first.click()
                        await page.wait_for_timeout(3000)

                    # Extract review blocks
                    review_blocks = page.locator(
                        '[class*="review"], [data-test="review"]'
                    )
                    count = min(await review_blocks.count(), 20)

                    for i in range(count):
                        try:
                            block = review_blocks.nth(i)
                            text = await block.inner_text()

                            # Parse pros/cons structure
                            pros = ""
                            cons = ""
                            if "Pros" in text and "Cons" in text:
                                parts = text.split("Cons")
                                pros_part = parts[0]
                                cons = parts[1] if len(parts) > 1 else ""
                                pros = pros_part.split("Pros")[-1] if "Pros" in pros_part else pros_part

                            review_text = f"Pros: {pros.strip()}\nCons: {cons.strip()}" if pros or cons else text

                            results.append(
                                RawResult(
                                    source_platform="glassdoor",
                                    source_url=page.url,
                                    raw_text=self._safe_text(review_text),
                                    rating=overall_rating,
                                    reviewer_type="employee",
                                    metadata={
                                        "type": "employee_review",
                                        "pros": pros.strip(),
                                        "cons": cons.strip(),
                                        "source_site": "glassdoor",
                                    },
                                )
                            )
                        except Exception:
                            continue

                except Exception as e:
                    self.logger.warning(f"Glassdoor page error: {e}")

                await browser.close()

        except Exception as e:
            self.logger.warning(f"Glassdoor crawl error: {e}")

        return results

    async def _crawl_indeed(self, company: str) -> list[RawResult]:
        """Crawl Indeed for reviews."""
        results = []

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                search_url = (
                    f"https://www.indeed.com/cmp/{company.replace(' ', '-')}/reviews"
                    f"?fcountry=LK"
                )

                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)

                    # Extract review elements
                    review_blocks = page.locator(
                        '[data-testid="review"], [class*="review-container"]'
                    )
                    count = min(await review_blocks.count(), 20)

                    for i in range(count):
                        try:
                            block = review_blocks.nth(i)
                            text = await block.inner_text()

                            results.append(
                                RawResult(
                                    source_platform="glassdoor",
                                    source_url=page.url,
                                    raw_text=self._safe_text(text),
                                    reviewer_type="employee",
                                    metadata={
                                        "type": "employee_review",
                                        "source_site": "indeed",
                                    },
                                )
                            )
                        except Exception:
                            continue

                except Exception as e:
                    self.logger.warning(f"Indeed page error: {e}")

                await browser.close()

        except Exception as e:
            self.logger.warning(f"Indeed crawl error: {e}")

        return results
