"""
Google Maps crawler using requests + BeautifulSoup.
Extracts business ratings, review count, and text reviews for Sri Lankan locations.
"""

import logging
import re
from typing import Optional
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"


class GoogleMapsCrawler(BaseCrawler):
    """Crawls Google Maps for Sri Lankan business reviews."""

    def __init__(self, max_results: int = 20):
        super().__init__(name="google_maps", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search Google Maps for company reviews.

        Uses Playwright for headless browsing to render dynamic content.

        Args:
            query: Search query (e.g. "WSO2 Sri Lanka").
            company: Normalized company name.

        Returns:
            List of RawResult objects from Google Maps.
        """
        results = []

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.warning(
                "Playwright not installed. Skipping Google Maps crawler."
            )
            return results

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    locale="en-US",
                    geolocation={"latitude": 6.9271, "longitude": 79.8612},
                    permissions=["geolocation"],
                )
                page = await context.new_page()

                # Search Google Maps
                search_url = f"{GOOGLE_MAPS_SEARCH_URL}{query.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                # Try to find the business listing
                content = await page.content()

                # Extract rating from page
                rating_match = re.search(r'(\d+\.?\d*)\s*stars?', content, re.I)
                review_count_match = re.search(r'(\d[\d,]*)\s*reviews?', content, re.I)

                star_rating = float(rating_match.group(1)) if rating_match else None
                review_count = (
                    int(review_count_match.group(1).replace(",", ""))
                    if review_count_match
                    else 0
                )

                # Add basic business info
                if star_rating is not None:
                    results.append(
                        RawResult(
                            source_platform="google_maps",
                            source_url=page.url,
                            raw_text=f"{company} on Google Maps: {star_rating} stars, {review_count} reviews",
                            rating=star_rating,
                            reviewer_type="customer",
                            metadata={
                                "star_rating": star_rating,
                                "review_count": review_count,
                                "type": "business_listing",
                            },
                        )
                    )

                # Try to click on reviews tab and extract individual reviews
                try:
                    reviews_tab = page.locator('button:has-text("Reviews")')
                    if await reviews_tab.count() > 0:
                        await reviews_tab.first.click()
                        await page.wait_for_timeout(2000)

                        # Scroll to load reviews
                        for _ in range(3):
                            await page.mouse.wheel(0, 500)
                            await page.wait_for_timeout(1000)

                        # Extract review elements
                        review_elements = page.locator('[data-review-id]')
                        count = min(await review_elements.count(), self.max_results)

                        for i in range(count):
                            try:
                                element = review_elements.nth(i)
                                text = await element.inner_text()

                                # Try to extract individual rating
                                individual_rating = None
                                aria = await element.get_attribute("aria-label") or ""
                                rating_in_review = re.search(r'(\d+)\s*star', aria, re.I)
                                if rating_in_review:
                                    individual_rating = float(rating_in_review.group(1))

                                results.append(
                                    RawResult(
                                        source_platform="google_maps",
                                        source_url=page.url,
                                        raw_text=self._safe_text(text),
                                        rating=individual_rating,
                                        reviewer_type="customer",
                                        metadata={
                                            "type": "review",
                                            "review_index": i,
                                        },
                                    )
                                )
                            except Exception:
                                continue

                except Exception as e:
                    self.logger.warning(f"Could not extract individual reviews: {e}")

                await browser.close()

        except Exception as e:
            self.logger.error(f"Google Maps crawl error: {e}")

        self.logger.info(
            f"Google Maps crawler found {len(results)} results for '{company}'"
        )
        return results
