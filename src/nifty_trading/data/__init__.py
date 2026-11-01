"""Data package exports."""

from nifty_trading.data.calendar import NSECalendar
from nifty_trading.data.downloader import BatchRecord, HistoricalDataDownloader
from nifty_trading.data.duckdb_interface import DuckDBEngine, duckdb_engine
from nifty_trading.data.storage import (
    CANDLE_ARROW_SCHEMA,
    ParquetStorage,
    get_available_date_range,
    get_data_summary,
    load_candles,
    verify_dataset,
    write_partition,
)
from nifty_trading.data.validator import DataQualityValidator, ValidationReport

__all__ = [
    "NSECalendar",
    "HistoricalDataDownloader",
    "BatchRecord",
    "DuckDBEngine",
    "duckdb_engine",
    "ParquetStorage",
    "CANDLE_ARROW_SCHEMA",
    "write_partition",
    "load_candles",
    "get_available_date_range",
    "get_data_summary",
    "verify_dataset",
    "DataQualityValidator",
    "ValidationReport",
]

