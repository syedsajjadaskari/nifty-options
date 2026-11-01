"""Unit tests for candle parsing, validation, price consistency, and deduplication."""

import pandas as pd

from nifty_trading.data.downloader import HistoricalDataDownloader


def test_clean_and_validate_raw_df_valid():
    """Verify standard raw dataframe parsing and column renaming."""
    downloader = HistoricalDataDownloader()
    raw = pd.DataFrame({
        "Datetime": ["2025-09-01T09:15:00", "2025-09-01T09:16:00"],
        "Open": [24500.0, 24510.0],
        "High": [24520.0, 24530.0],
        "Low": [24490.0, 24505.0],
        "Close": [24515.0, 24525.0],
        "Volume": [0, 0],
    })

    clean, rejected = downloader.clean_and_validate_raw_df(raw)
    assert len(clean) == 2
    assert rejected == 0
    assert list(clean.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert str(clean["timestamp"].dt.tz) == "Asia/Kolkata"


def test_clean_and_validate_price_inconsistencies():
    """Verify rejection of corrupted candles (High < Low, negative prices)."""
    downloader = HistoricalDataDownloader()
    raw = pd.DataFrame({
        "Datetime": [
            "2025-09-01T09:15:00",
            "2025-09-01T09:16:00",  # High < Low (bad)
            "2025-09-01T09:17:00",  # Negative price (bad)
        ],
        "Open": [24500.0, 24500.0, -100.0],
        "High": [24520.0, 24400.0, 100.0],
        "Low": [24490.0, 24600.0, -200.0],
        "Close": [24515.0, 24450.0, 50.0],
        "Volume": [0, 0, 0],
    })

    clean, rejected = downloader.clean_and_validate_raw_df(raw)
    assert len(clean) == 1
    assert rejected == 2
    assert clean["open"].iloc[0] == 24500.0


def test_clean_and_validate_deduplication():
    """Verify deterministic deduplication by timestamp keeping last."""
    downloader = HistoricalDataDownloader()
    raw = pd.DataFrame({
        "Datetime": ["2025-09-01T09:15:00", "2025-09-01T09:15:00"],
        "Open": [24500.0, 24505.0],
        "High": [24520.0, 24525.0],
        "Low": [24490.0, 24495.0],
        "Close": [24515.0, 24520.0],
        "Volume": [0, 10],
    })

    clean, rejected = downloader.clean_and_validate_raw_df(raw)
    assert len(clean) == 1
    assert clean["close"].iloc[0] == 24520.0  # Kept last
