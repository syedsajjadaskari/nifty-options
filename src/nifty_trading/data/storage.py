"""Parquet storage engine with ZSTD compression and partitioned layout."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from nifty_trading.config.settings import Settings, settings

logger = logging.getLogger(__name__)

# Standard PyArrow schema for 1-minute OHLCV candles
CANDLE_ARROW_SCHEMA = pa.schema([
    ("timestamp", pa.timestamp("us", tz="Asia/Kolkata")),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.int64()),  # Nullable integer
])


class ParquetStorage:
    """Manages writing and reading partitioned Parquet datasets with ZSTD compression."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self.processed_dir = self.settings.processed_data_dir

    def get_partition_dir(self, year: int, month: int, instrument_symbol: str = "nifty50") -> Path:
        """Construct directory path for a specific partition."""
        month_str = f"{month:02d}"
        return self.processed_dir / instrument_symbol.lower() / f"year={year}" / f"month={month_str}"

    def get_partition_file(self, year: int, month: int, instrument_symbol: str = "nifty50") -> Path:
        """Construct file path for a partition parquet file."""
        return self.get_partition_dir(year, month, instrument_symbol) / "candles.parquet"

    def write_partition(
        self,
        df: pd.DataFrame,
        year: int,
        month: int,
        instrument_symbol: str = "nifty50",
    ) -> Path:
        """Atomically write cleaned candle dataframe to partitioned Parquet with ZSTD compression."""
        if df.empty:
            raise ValueError(f"Cannot write empty dataframe to partition {year}-{month:02d}")

        partition_dir = self.get_partition_dir(year, month, instrument_symbol)
        partition_dir.mkdir(parents=True, exist_ok=True)
        target_file = partition_dir / "candles.parquet"
        temp_file = partition_dir / "candles.parquet.tmp"

        # Standardize columns and deduplicate
        clean_df = df.copy()

        # Ensure timestamp is datetime with Asia/Kolkata timezone
        if not pd.api.types.is_datetime64_any_dtype(clean_df["timestamp"]):
            clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])

        if clean_df["timestamp"].dt.tz is None:
            clean_df["timestamp"] = clean_df["timestamp"].dt.tz_localize("Asia/Kolkata")
        else:
            clean_df["timestamp"] = clean_df["timestamp"].dt.tz_convert("Asia/Kolkata")

        # Deterministic deduplication by timestamp, keeping last
        clean_df = clean_df.drop_duplicates(subset=["timestamp"], keep="last")

        # Sort chronologically
        clean_df = clean_df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)

        # Cast numeric columns
        clean_df["open"] = clean_df["open"].astype("float64")
        clean_df["high"] = clean_df["high"].astype("float64")
        clean_df["low"] = clean_df["low"].astype("float64")
        clean_df["close"] = clean_df["close"].astype("float64")

        if "volume" in clean_df.columns:
            clean_df["volume"] = pd.to_numeric(clean_df["volume"], errors="coerce").fillna(0).astype("int64")
        else:
            clean_df["volume"] = 0

        # Select exact schema columns
        clean_df = clean_df[["timestamp", "open", "high", "low", "close", "volume"]]

        # Custom metadata
        custom_metadata = {
            "instrument": instrument_symbol.upper(),
            "timeframe": "1m",
            "year": str(year),
            "month": f"{month:02d}",
            "row_count": str(len(clean_df)),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "first_timestamp": clean_df["timestamp"].iloc[0].isoformat(),
            "last_timestamp": clean_df["timestamp"].iloc[-1].isoformat(),
        }

        # Convert to PyArrow Table
        table = pa.Table.from_pandas(clean_df, schema=CANDLE_ARROW_SCHEMA, preserve_index=False)
        existing_meta = table.schema.metadata or {}
        existing_meta.update({k.encode("utf-8"): v.encode("utf-8") for k, v in custom_metadata.items()})
        table = table.replace_schema_metadata(existing_meta)

        # Write to temporary file with ZSTD compression
        pq.write_table(
            table,
            temp_file,
            compression="zstd",
            compression_level=7,
            use_dictionary=True,
        )

        # Atomic rename
        temp_file.replace(target_file)
        logger.info(
            "Saved partition %s (rows: %d, size: %d bytes)",
            target_file,
            len(clean_df),
            target_file.stat().st_size,
        )
        return target_file

    def list_all_partitions(self, instrument_symbol: str = "nifty50") -> list[Path]:
        """List all available partition parquet files sorted chronologically."""
        base_dir = self.processed_dir / instrument_symbol.lower()
        if not base_dir.exists():
            return []
        files = sorted(base_dir.glob("year=*/month=*/candles.parquet"))
        return files

    def load_candles(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        instrument_symbol: str = "nifty50",
    ) -> pd.DataFrame:
        """Load candles across partitions, optionally filtered by date range."""
        files = self.list_all_partitions(instrument_symbol)
        if not files:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        tables = []
        for f in files:
            t = pq.read_table(f)
            tables.append(t)

        combined = pa.concat_tables(tables)
        df = combined.to_pandas()

        if start_date:
            start_ts = pd.Timestamp(start_date, tz="Asia/Kolkata")
            df = df[df["timestamp"] >= start_ts]

        if end_date:
            # End of specified date
            end_ts = pd.Timestamp(end_date, tz="Asia/Kolkata") + pd.Timedelta(days=1)
            df = df[df["timestamp"] < end_ts]

        return df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)

    def get_available_date_range(
        self, instrument_symbol: str = "nifty50"
    ) -> tuple[str, str] | None:
        """Return (first_date, last_date) available in dataset."""
        files = self.list_all_partitions(instrument_symbol)
        if not files:
            return None

        # Read first file's first timestamp and last file's last timestamp
        first_table = pq.read_table(files[0], columns=["timestamp"])
        last_table = pq.read_table(files[-1], columns=["timestamp"])

        if first_table.num_rows == 0 or last_table.num_rows == 0:
            return None

        first_ts = first_table["timestamp"][0].as_py()
        last_ts = last_table["timestamp"][-1].as_py()

        return (
            first_ts.strftime("%Y-%m-%d %H:%M:%S"),
            last_ts.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def get_data_summary(self, instrument_symbol: str = "nifty50") -> dict[str, Any]:
        """Summarize total candles, size on disk, partitions, and date span."""
        files = self.list_all_partitions(instrument_symbol)
        total_size = sum(f.stat().st_size for f in files)
        date_range = self.get_available_date_range(instrument_symbol)

        total_rows = 0
        partition_details = []

        for f in files:
            meta = pq.read_metadata(f)
            num_rows = meta.num_rows
            total_rows += num_rows
            partition_details.append({
                "path": str(f.relative_to(self.settings.project_root)),
                "rows": num_rows,
                "size_bytes": f.stat().st_size,
            })

        return {
            "instrument": instrument_symbol.upper(),
            "partition_count": len(files),
            "total_candles": total_rows,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "date_range": date_range,
            "partitions": partition_details,
        }

    def verify_dataset(self, instrument_symbol: str = "nifty50") -> dict[str, Any]:
        """Verify structural dataset integrity across all partitions."""
        summary = self.get_data_summary(instrument_symbol)
        files = self.list_all_partitions(instrument_symbol)

        is_valid = True
        errors = []

        if not files:
            return {"status": "FAILED", "reason": "No partitions found", "summary": summary}

        prev_timestamp = None
        for f in files:
            try:
                table = pq.read_table(f)
                df = table.to_pandas()
                # Check sorted and unique
                if not df["timestamp"].is_monotonic_increasing:
                    is_valid = False
                    errors.append(f"Partition {f.name} timestamps not monotonic")
                if df["timestamp"].duplicated().any():
                    is_valid = False
                    errors.append(f"Partition {f.name} contains duplicate timestamps")
                if prev_timestamp and df["timestamp"].iloc[0] <= prev_timestamp:
                    is_valid = False
                    errors.append(f"Overlap detected between partitions before {df['timestamp'].iloc[0]}")
                prev_timestamp = df["timestamp"].iloc[-1]
            except Exception as e:
                is_valid = False
                errors.append(f"Error reading partition {f}: {e}")

        return {
            "status": "VALID" if is_valid else "INVALID",
            "errors": errors,
            "summary": summary,
        }


# Convenience module-level functions
_default_storage = ParquetStorage()


def write_partition(df: pd.DataFrame, year: int, month: int, instrument_symbol: str = "nifty50") -> Path:
    return _default_storage.write_partition(df, year, month, instrument_symbol)


def load_candles(start_date: str | None = None, end_date: str | None = None, instrument_symbol: str = "nifty50") -> pd.DataFrame:
    return _default_storage.load_candles(start_date, end_date, instrument_symbol)


def get_available_date_range(instrument_symbol: str = "nifty50") -> tuple[str, str] | None:
    return _default_storage.get_available_date_range(instrument_symbol)


def get_data_summary(instrument_symbol: str = "nifty50") -> dict[str, Any]:
    return _default_storage.get_data_summary(instrument_symbol)


def verify_dataset(instrument_symbol: str = "nifty50") -> dict[str, Any]:
    return _default_storage.verify_dataset(instrument_symbol)
