"""
Base crawler class and shared data structures.
All crawlers inherit from BaseCrawler.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class RawResult:
    """A single raw result from any crawler source."""

    source_platform: str
    source_url: str
    raw_text: str
    date: Optional[str] = None
    rating: Optional[float] = None
    reviewer_type: str = "general"  # employee, customer, job_seeker, press, general
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RawResult":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BaseCrawler(ABC):
    """
    Abstract base class for all crawlers.
    Each crawler must implement the `crawl` method.
    """

    def __init__(self, name: str, max_results: int = 30):
        self.name = name
        self.max_results = max_results
        self.logger = logging.getLogger(f"crawler.{name}")

    @abstractmethod
    async def crawl(self, query: str, company: str) -> list[RawResult]:
        """
        Crawl the source platform for company data.

        Args:
            query: The enriched search query.
            company: The normalized company name.

        Returns:
            List of RawResult objects.
        """
        pass

    def _safe_text(self, text: str, max_length: int = 5000) -> str:
        """Safely truncate and clean text."""
        if not text:
            return ""
        text = text.strip()
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text

    def _format_date(self, timestamp) -> Optional[str]:
        """Convert various timestamp formats to ISO string."""
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).isoformat()
            elif isinstance(timestamp, datetime):
                return timestamp.isoformat()
            elif isinstance(timestamp, str):
                return timestamp
        except Exception:
            return None
        return None
