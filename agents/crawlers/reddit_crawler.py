"""
Reddit crawler using PRAW.
Searches r/srilanka, r/colombo, r/askSriLanka for company mentions.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from .base_crawler import BaseCrawler, RawResult

logger = logging.getLogger(__name__)

SUBREDDITS = ["srilanka", "colombo", "askSriLanka"]
MAX_COMMENTS_PER_POST = 5
MAX_AGE_YEARS = 2


class RedditCrawler(BaseCrawler):
    """Crawls Reddit for Sri Lanka-related company discussions."""

    def __init__(self, max_results: int = 30):
        super().__init__(name="reddit", max_results=max_results)
        self._reddit = None

    def _get_reddit(self):
        """Initialize PRAW Reddit instance."""
        if self._reddit is None:
            try:
                import praw
                self._reddit = praw.Reddit(
                    client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
                    client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
                    user_agent=os.environ.get(
                        "REDDIT_USER_AGENT", "CompanyCareerScout/1.0"
                    ),
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize PRAW: {e}")
                raise
        return self._reddit

    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Search Reddit for company mentions.

        Args:
            query: Search query (e.g. "WSO2 Sri Lanka").
            company: Normalized company name.

        Returns:
            List of RawResult objects from Reddit.
        """
        results = []
        cutoff_date = datetime.now() - timedelta(days=MAX_AGE_YEARS * 365)

        try:
            reddit = self._get_reddit()
        except Exception as e:
            self.logger.warning(f"Reddit unavailable: {e}")
            return results

        try:
            for subreddit_name in SUBREDDITS:
                if len(results) >= self.max_results:
                    break

                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    search_results = subreddit.search(
                        query, sort="relevance", time_filter="all", limit=15
                    )

                    for post in search_results:
                        if len(results) >= self.max_results:
                            break

                        # Check age
                        post_date = datetime.fromtimestamp(post.created_utc)
                        if post_date < cutoff_date:
                            continue

                        # Add the post itself
                        post_text = f"{post.title}\n\n{post.selftext}" if post.selftext else post.title
                        results.append(
                            RawResult(
                                source_platform="reddit",
                                source_url=f"https://reddit.com{post.permalink}",
                                raw_text=self._safe_text(post_text),
                                date=self._format_date(post.created_utc),
                                rating=None,
                                reviewer_type="general",
                                metadata={
                                    "subreddit": subreddit_name,
                                    "score": post.score,
                                    "num_comments": post.num_comments,
                                    "type": "post",
                                },
                            )
                        )

                        # Add top comments
                        try:
                            post.comments.replace_more(limit=0)
                            top_comments = sorted(
                                post.comments.list(),
                                key=lambda c: c.score,
                                reverse=True,
                            )[:MAX_COMMENTS_PER_POST]

                            for comment in top_comments:
                                if len(results) >= self.max_results:
                                    break
                                if not comment.body or comment.body == "[deleted]":
                                    continue

                                results.append(
                                    RawResult(
                                        source_platform="reddit",
                                        source_url=f"https://reddit.com{comment.permalink}",
                                        raw_text=self._safe_text(comment.body),
                                        date=self._format_date(comment.created_utc),
                                        rating=None,
                                        reviewer_type="general",
                                        metadata={
                                            "subreddit": subreddit_name,
                                            "score": comment.score,
                                            "type": "comment",
                                            "parent_post": post.title,
                                        },
                                    )
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Error fetching comments for post {post.id}: {e}"
                            )

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
