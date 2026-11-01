"""Unit tests for Parquet storage, ZSTD compression, and DuckDB analytical queries."""

from pathlib import Path

import pandas as pd
import pytest

from nifty_trading.config.settings import Settings
from nifty_trading.data.duckdb_interface import DuckDBEngine
from nifty_trading.data.storage import ParquetStorage


@pytest.fixture
def temp_storage(tmp_path: Path):
    settings_obj = Settings()
    # Override processed_dir to temp path
    storage = ParquetStorage(settings_obj)
    storage.processed_dir = tmp_path / "processed"
    return storage, tmp_path / "processed"


def test_parquet_write_and_load(temp_storage):
    """Verify writing partitioned Parquet with ZSTD compression and reloading."""
    storage, processed_dir = temp_storage

    sample_df = pd.DataFrame({
        "timestamp": pd.date_range("2025-09-01 09:15:00", periods=5, freq="1min", tz="Asia/Kolkata"),
        "open": [24500.0, 24501.0, 24502.0, 24503.0, 24504.0],
        "high": [24510.0, 24511.0, 24512.0, 24513.0, 24514.0],
        "low": [24490.0, 24491.0, 24492.0, 24493.0, 24494.0],
        "close": [24505.0, 24506.0, 24507.0, 24508.0, 24509.0],
        "volume": [0, 0, 0, 0, 0],
    })

    file_path = storage.write_partition(sample_df, year=2025, month=9, instrument_symbol="test_nifty")
    assert file_path.exists()
    assert "year=2025/month=09/candles.parquet" in str(file_path)

    # Reload candles
    loaded = storage.load_candles(instrument_symbol="test_nifty")
    assert len(loaded) == 5
    assert loaded["close"].iloc[-1] == 24509.0


def test_duckdb_direct_query():
    """Verify DuckDB zero-copy querying of actual repository Parquet dataset."""
    engine = DuckDBEngine()
    count = engine.get_candle_count()
    assert count > 0

    stats = engine.get_summary_stats()
    assert not stats.empty
    assert stats["total_candles"].iloc[0] == count
    assert stats["all_time_low"].iloc[0] > 0
    assert stats["all_time_high"].iloc[0] > stats["all_time_low"].iloc[0]
