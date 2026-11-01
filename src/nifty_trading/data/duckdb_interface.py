"""DuckDB analytical query engine querying Parquet directly without data duplication."""

import logging
from typing import Any

import duckdb
import pandas as pd

from nifty_trading.config.settings import Settings, settings

logger = logging.getLogger(__name__)


class DuckDBEngine:
    """Zero-copy analytical query layer querying partitioned Parquet via DuckDB."""

    def __init__(self, app_settings: Settings = settings, db_path: str = ":memory:"):
        self.settings = app_settings
        self.db_path = db_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(database=self.db_path)
            self._register_views()
        return self._conn

    def _get_parquet_glob(self, instrument: str = "nifty50") -> str:
        glob_path = self.settings.processed_data_dir / instrument.lower() / "year=*" / "month=*" / "candles.parquet"
        return str(glob_path)

    def _register_views(self) -> None:
        """Register views for available instruments pointing to Parquet files."""
        glob_str = self._get_parquet_glob("nifty50")
        try:
            # Check if any matching files exist
            files = list(self.settings.processed_data_dir.glob("nifty50/year=*/month=*/candles.parquet"))
            if files:
                self.conn.execute(
                    f"CREATE OR REPLACE VIEW nifty50 AS SELECT * FROM read_parquet('{glob_str}')"
                )
                logger.debug("Registered DuckDB view 'nifty50' from %s", glob_str)
        except Exception as e:
            logger.warning("Could not register default nifty50 view: %s", e)

    def refresh_views(self) -> None:
        """Re-create views if new partitions were downloaded."""
        self._register_views()

    def query(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        """Execute arbitrary SQL query against Parquet views and return DataFrame."""
        self.refresh_views()
        if params:
            return self.conn.execute(sql, params).df()
        return self.conn.execute(sql).df()

    def get_candle_count(self) -> int:
        """Return total count of candles in nifty50 view."""
        self.refresh_views()
        res = self.conn.execute("SELECT count(*) FROM nifty50").fetchone()
        return res[0] if res else 0

    def get_summary_stats(self) -> pd.DataFrame:
        """Return high-level OHLCV aggregated statistics."""
        self.refresh_views()
        query = """
        SELECT
            count(*) as total_candles,
            min(timestamp) as first_timestamp,
            max(timestamp) as last_timestamp,
            min(low) as all_time_low,
            max(high) as all_time_high,
            avg(close) as avg_close,
            count(distinct strftime(timestamp, '%Y-%m-%d')) as trading_days_count
        FROM nifty50
        """
        return self.conn.execute(query).df()

    def sample_candles(self, limit: int = 5) -> pd.DataFrame:
        """Fetch head rows for quick inspection."""
        self.refresh_views()
        return self.conn.execute(
            f"SELECT * FROM nifty50 ORDER BY timestamp ASC LIMIT {limit}"
        ).df()

    def query_date(self, date_str: str) -> pd.DataFrame:
        """Query all 1-minute bars for a specific date (YYYY-MM-DD)."""
        self.refresh_views()
        sql = """
        SELECT * FROM nifty50
        WHERE strftime(timestamp, '%Y-%m-%d') = ?
        ORDER BY timestamp ASC
        """
        return self.conn.execute(sql, [date_str]).df()


# Global singleton instance
duckdb_engine = DuckDBEngine()
