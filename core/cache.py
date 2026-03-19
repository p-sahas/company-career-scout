"""
SQLite-based cache manager for Company Career Scout.
Caches raw scraped results per company with 48-hour TTL.
Also tracks LLM token usage per run.
"""

import sqlite3
import json
import time
import os
from typing import Optional
from datetime import datetime


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "cache.db"
)
DEFAULT_TTL_SECONDS = 48 * 60 * 60  # 48 hours


class CacheManager:
    """
    SQLite cache for scraped company data.
    Supports TTL-based expiration and token usage logging.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS crawl_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL,
                    UNIQUE(company, source)
                );

                CREATE TABLE IF NOT EXISTS analysis_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    cached_at REAL NOT NULL,
                    UNIQUE(company)
                );

                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    calls_made INTEGER NOT NULL,
                    run_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_crawl_company
                    ON crawl_cache(company, source);
                CREATE INDEX IF NOT EXISTS idx_analysis_company
                    ON analysis_cache(company);
            """)
            conn.commit()
        finally:
            conn.close()

    def get(self, company: str, source: str) -> Optional[list]:
        """
        Get cached crawl results for a company+source combination.

        Args:
            company: Normalized company name.
            source: Source platform identifier.

        Returns:
            Cached data list or None if expired/missing.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data, cached_at FROM crawl_cache WHERE company = ? AND source = ?",
                (company.lower(), source.lower()),
            ).fetchone()

            if row is None:
                return None

            age = time.time() - row["cached_at"]
            if age > self.ttl_seconds:
                # Expired — delete and return None
                conn.execute(
                    "DELETE FROM crawl_cache WHERE company = ? AND source = ?",
                    (company.lower(), source.lower()),
                )
                conn.commit()
                return None

            return json.loads(row["data"])
        finally:
            conn.close()

    def set(self, company: str, source: str, data: list):
        """
        Cache crawl results for a company+source combination.

        Args:
            company: Normalized company name.
            source: Source platform identifier.
            data: List of raw result dicts to cache.
        """
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO crawl_cache (company, source, data, cached_at)
                   VALUES (?, ?, ?, ?)""",
                (company.lower(), source.lower(), json.dumps(data), time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_analysis(self, company: str) -> Optional[dict]:
        """
        Get cached analysis report for a company.

        Args:
            company: Normalized company name.

        Returns:
            Cached report dict or None if expired/missing.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT report_json, cached_at FROM analysis_cache WHERE company = ?",
                (company.lower(),),
            ).fetchone()

            if row is None:
                return None

            age = time.time() - row["cached_at"]
            if age > self.ttl_seconds:
                conn.execute(
                    "DELETE FROM analysis_cache WHERE company = ?",
                    (company.lower(),),
                )
                conn.commit()
                return None

            return json.loads(row["report_json"])
        finally:
            conn.close()

    def set_analysis(self, company: str, report: dict, model_used: str):
        """Cache an analysis report."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO analysis_cache (company, report_json, model_used, cached_at)
                   VALUES (?, ?, ?, ?)""",
                (company.lower(), json.dumps(report), model_used, time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_cache_age(self, company: str, source: str) -> Optional[float]:
        """
        Get the age of cached data in seconds.

        Returns:
            Age in seconds or None if no cache exists.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT cached_at FROM crawl_cache WHERE company = ? AND source = ?",
                (company.lower(), source.lower()),
            ).fetchone()

            if row is None:
                return None

            return time.time() - row["cached_at"]
        finally:
            conn.close()

    def get_cache_age_display(self, company: str, source: str) -> Optional[str]:
        """Get a human-readable cache age string."""
        age = self.get_cache_age(company, source)
        if age is None:
            return None

        hours = int(age // 3600)
        minutes = int((age % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m ago"
        return f"{minutes}m ago"

    def log_token_usage(
        self,
        company: str,
        provider: str,
        model: str,
        tokens_used: int,
        calls_made: int,
    ):
        """
        Log LLM token usage for a run.

        Args:
            company: Company that was analyzed.
            provider: LLM provider name.
            model: Model name used.
            tokens_used: Total tokens consumed.
            calls_made: Number of LLM calls made.
        """
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO token_usage (company, provider, model, tokens_used, calls_made, run_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    company.lower(),
                    provider,
                    model,
                    tokens_used,
                    calls_made,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_total_tokens(self) -> int:
        """Get total tokens used across all runs."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(tokens_used), 0) as total FROM token_usage"
            ).fetchone()
            return row["total"]
        finally:
            conn.close()

    def clear_company_cache(self, company: str):
        """Clear all cached data for a specific company."""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM crawl_cache WHERE company = ?", (company.lower(),)
            )
            conn.execute(
                "DELETE FROM analysis_cache WHERE company = ?", (company.lower(),)
            )
            conn.commit()
        finally:
            conn.close()

    def clear_all(self):
        """Clear all cached data."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM crawl_cache")
            conn.execute("DELETE FROM analysis_cache")
            conn.commit()
        finally:
            conn.close()
