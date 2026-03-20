"""
Reddit crawler using Reddit's public JSON API.
No authentication (PRAW) required — uses old.reddit.com/search.json endpoints.
Searches r/srilanka, r/colombo, r/askSriLanka for company mentions.
"""

import logging
from datetime import datetime, timedelta
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)

# Import crawler settings from config
try:
    from config.settings import (
        REDDIT_SUBREDDITS,
        REDDIT_MAX_POSTS,
        REDDIT_MAX_COMMENTS_PER_POST,
        REDDIT_MAX_AGE_YEARS,
        REDDIT_USER_AGENT,
    )
except ImportError:
    REDDIT_SUBREDDITS = ["srilanka", "colombo", "askSriLanka"]
    REDDIT_MAX_POSTS = 30
    REDDIT_MAX_COMMENTS_PER_POST = 5
    REDDIT_MAX_AGE_YEARS = 2
    REDDIT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )


class RedditCrawler(BaseCrawler):
    """Crawls Reddit for Sri Lanka-related company discussions using the public JSON API."""

    def __init__(self, max_results: int = REDDIT_MAX_POSTS):
        super().__init__(name="reddit", max_results=max_results)

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search Reddit via public JSON API (no auth needed).

        Args:
            query: Search query (e.g. "WSO2 Sri Lanka").
            company: Normalized company name.

        Returns:
            List of RawResult objects from Reddit.
        """
        results = []
        cutoff_date = datetime.now() - timedelta(days=REDDIT_MAX_AGE_YEARS * 365)

        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": REDDIT_USER_AGENT},
            ) as client:
                for subreddit_name in REDDIT_SUBREDDITS:
                    if len(results) >= self.max_results:
                        break

                    try:
                        # Use old.reddit.com JSON search endpoint
                        search_url = (
                            f"https://old.reddit.com/r/{subreddit_name}/search.json"
                        )
                        params = {
                            "q": query,
                            "sort": "relevance",
                            "t": "all",
                            "limit": 15,
                            "restrict_sr": "on",
                        }

                        response = await client.get(search_url, params=params)

                        if response.status_code != 200:
                            self.logger.warning(
                                f"Reddit search returned {response.status_code} "
                                f"for r/{subreddit_name}"
                            )
                            continue

                        data = response.json()
                        posts = data.get("data", {}).get("children", [])

                        for post_wrapper in posts:
                            if len(results) >= self.max_results:
                                break

                            post = post_wrapper.get("data", {})

                            # Check age
                            created_utc = post.get("created_utc", 0)
                            post_date = datetime.fromtimestamp(created_utc)
                            if post_date < cutoff_date:
                                continue

                            # Build post text
                            title = post.get("title", "")
                            selftext = post.get("selftext", "")
                            post_text = f"{title}\n\n{selftext}" if selftext else title

                            permalink = post.get("permalink", "")
                            post_url = f"https://reddit.com{permalink}"

                            results.append(
                                RawResult(
                                    source_platform="reddit",
                                    source_url=post_url,
                                    raw_text=self._safe_text(post_text),
                                    date=self._format_date(created_utc),
                                    rating=None,
                                    reviewer_type="general",
                                    metadata={
                                        "subreddit": subreddit_name,
                                        "score": post.get("score", 0),
                                        "num_comments": post.get("num_comments", 0),
                                        "type": "post",
                                    },
                                )
                            )

                            # Fetch top comments for this post
                            if permalink:
                                comment_results = await self._fetch_comments(
                                    client, permalink, subreddit_name, title
                                )
                                results.extend(comment_results)

                    except Exception as e:
                        self.logger.warning(
                            f"Error searching r/{subreddit_name}: {e}"
                        )
                        continue

        except Exception as e:
            self.logger.error(f"Reddit crawl error: {e}")

        self.logger.info(
            f"Reddit crawler found {len(results)} results for '{company}'"
        )
        return results

    async def _fetch_comments(
        self,
        client,
        permalink: str,
        subreddit: str,
        parent_title: str,
    ) -> list[RawResult]:
        """Fetch top comments for a post via JSON API."""
        comments = []

        try:
            comment_url = f"https://old.reddit.com{permalink}.json"
            params = {"sort": "top", "limit": REDDIT_MAX_COMMENTS_PER_POST}

            response = await client.get(comment_url, params=params)

            if response.status_code != 200:
                return comments

            data = response.json()

            # Reddit returns [post_listing, comment_listing]
            if len(data) < 2:
                return comments

            comment_children = data[1].get("data", {}).get("children", [])

            for comment_wrapper in comment_children[:REDDIT_MAX_COMMENTS_PER_POST]:
                comment = comment_wrapper.get("data", {})
                body = comment.get("body", "")

                if not body or body == "[deleted]" or body == "[removed]":
                    continue

                comment_permalink = comment.get("permalink", "")
                comment_url_full = f"https://reddit.com{comment_permalink}" if comment_permalink else ""

                comments.append(
                    RawResult(
                        source_platform="reddit",
                        source_url=comment_url_full,
                        raw_text=self._safe_text(body),
                        date=self._format_date(comment.get("created_utc", 0)),
                        rating=None,
                        reviewer_type="general",
                        metadata={
                            "subreddit": subreddit,
                            "score": comment.get("score", 0),
                            "type": "comment",
                            "parent_post": parent_title,
                        },
                    )
                )

        except Exception as e:
            self.logger.warning(f"Error fetching comments: {e}")

        return comments
