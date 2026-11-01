"""Resumable historical data downloader with rate-limiting, deduplication, and manifest tracking."""

import calendar
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from tqdm import tqdm

from nifty_trading.broker.client import BrokerClient
from nifty_trading.config.settings import Settings, settings
from nifty_trading.data.storage import ParquetStorage
from nifty_trading.instruments.resolver import InstrumentMetadata, InstrumentResolver

logger = logging.getLogger(__name__)


@dataclass
class BatchRecord:
    """Download manifest batch record."""

    batch_id: str
    year: int
    month: int
    start_date: str
    end_date: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED, FAILED, EMPTY
    candle_count: int = 0
    trading_days_count: int = 0
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    rejected_rows_count: int = 0
    parquet_path: str | None = None
    last_attempt_utc: str | None = None
    error_message: str | None = None


class HistoricalDataDownloader:
    """Manages downloading, validating, and persisting historical candle data."""

    def __init__(
        self,
        app_settings: Settings = settings,
        broker_client: BrokerClient | None = None,
        storage: ParquetStorage | None = None,
        resolver: InstrumentResolver | None = None,
    ):
        self.settings = app_settings
        self.broker = broker_client or BrokerClient(app_settings)
        self.storage = storage or ParquetStorage(app_settings)
        self.resolver = resolver or InstrumentResolver(app_settings)
        self.metadata_dir = self.settings.metadata_dir
        self.manifest_path = self.metadata_dir / "download_manifest.json"
        self._manifest: dict[str, Any] = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        """Load existing download manifest or initialize empty."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read manifest, starting fresh: %s", e)
        return {
            "instrument": "NIFTY",
            "timeframe": self.settings.data_timeframe,
            "batches": {},
            "last_updated_utc": None,
        }

    def _save_manifest(self) -> None:
        """Atomically persist manifest to disk."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._manifest["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        temp_path = self.manifest_path.with_suffix(".json.tmp")
        with open(temp_path, "w") as f:
            json.dump(self._manifest, f, indent=2)
        temp_path.replace(self.manifest_path)

    def generate_monthly_batches(
        self, start_date_str: str, end_date_str: str
    ) -> list[tuple[int, int, str, str]]:
        """Generate (year, month, start_date, end_date) tuples."""
        start_d = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_d = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        batches = []
        curr_year = start_d.year
        curr_month = start_d.month

        while (curr_year, curr_month) <= (end_d.year, end_d.month):
            last_day_of_month = calendar.monthrange(curr_year, curr_month)[1]
            batch_start = date(curr_year, curr_month, 1)
            batch_end = date(curr_year, curr_month, last_day_of_month)

            # Clamp boundaries
            if (curr_year, curr_month) == (start_d.year, start_d.month):
                batch_start = start_d
            if (curr_year, curr_month) == (end_d.year, end_d.month):
                batch_end = end_d

            batches.append((
                curr_year,
                curr_month,
                batch_start.strftime("%Y-%m-%d"),
                batch_end.strftime("%Y-%m-%d"),
            ))

            if curr_month == 12:
                curr_year += 1
                curr_month = 1
            else:
                curr_month += 1

        return batches

    def clean_and_validate_raw_df(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Standardize column names, validate prices, deduplicate, and reject malformed rows."""
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(), 0

        df = raw_df.copy()
        # Rename standard py5paisa columns to lowercase
        rename_map = {
            "Datetime": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
        df = df.rename(columns=rename_map)

        # Drop any rows with NaN in critical columns
        initial_len = len(df)
        df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])

        # Convert to numeric
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")
        else:
            df["volume"] = 0

        df = df.dropna(subset=["open", "high", "low", "close"])

        # OHLC price consistency filter:
        # High >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close, prices > 0
        valid_mask = (
            (df["open"] > 0)
            & (df["high"] > 0)
            & (df["low"] > 0)
            & (df["close"] > 0)
            & (df["high"] >= df["low"])
            & (df["high"] >= df["open"] * 0.999)  # Allow micro floating epsilon
            & (df["high"] >= df["close"] * 0.999)
            & (df["low"] <= df["open"] * 1.001)
            & (df["low"] <= df["close"] * 1.001)
        )

        valid_df = df[valid_mask].copy()
        rejected_count = initial_len - len(valid_df)

        if rejected_count > 0:
            logger.warning("Rejected %d malformed candles during validation", rejected_count)

        # Timestamp conversion & deduplication
        valid_df["timestamp"] = pd.to_datetime(valid_df["timestamp"])
        if valid_df["timestamp"].dt.tz is None:
            valid_df["timestamp"] = valid_df["timestamp"].dt.tz_localize("Asia/Kolkata")
        else:
            valid_df["timestamp"] = valid_df["timestamp"].dt.tz_convert("Asia/Kolkata")

        valid_df = valid_df.drop_duplicates(subset=["timestamp"], keep="last")
        valid_df = valid_df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)

        return valid_df, rejected_count

    def download_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        force: bool = False,
        instrument_meta: InstrumentMetadata | None = None,
    ) -> dict[str, Any]:
        """Download complete date range month-by-month with resume capability."""
        start_str = start_date or self.settings.data_start_date
        end_str = end_date or self.settings.data_end_date

        if instrument_meta is None:
            instrument_meta = self.resolver.resolve_nifty50_index()

        batches = self.generate_monthly_batches(start_str, end_str)
        logger.info(
            "Starting download for %s (%s) from %s to %s across %d monthly batches",
            instrument_meta.symbol,
            instrument_meta.scrip_code,
            start_str,
            end_str,
            len(batches),
        )

        overall_stats = {
            "total_batches": len(batches),
            "completed_batches": 0,
            "skipped_batches": 0,
            "failed_batches": 0,
            "total_candles": 0,
            "total_rejected": 0,
        }

        progress = tqdm(batches, desc="Downloading NIFTY 50 batches", unit="month")

        for year, month, batch_start, batch_end in progress:
            batch_id = f"{year}-{month:02d}"
            progress.set_postfix({"batch": batch_id})

            # Check if already completed
            existing = self._manifest["batches"].get(batch_id)
            partition_file = self.storage.get_partition_file(year, month, "nifty50")

            if not force and existing and existing.get("status") == "COMPLETED" and partition_file.exists():
                logger.debug("Skipping already completed batch %s", batch_id)
                overall_stats["skipped_batches"] += 1
                overall_stats["total_candles"] += existing.get("candle_count", 0)
                continue

            record = BatchRecord(
                batch_id=batch_id,
                year=year,
                month=month,
                start_date=batch_start,
                end_date=batch_end,
                status="IN_PROGRESS",
                last_attempt_utc=datetime.now(timezone.utc).isoformat(),
            )
            self._manifest["batches"][batch_id] = asdict(record)
            self._save_manifest()

            try:
                raw_df = self.broker.fetch_historical_candles(
                    exch=instrument_meta.exchange,
                    exchange_segment=instrument_meta.exchange_segment,
                    scrip_code=instrument_meta.scrip_code,
                    timeframe=self.settings.data_timeframe,
                    from_date=batch_start,
                    to_date=batch_end,
                )

                clean_df, rejected = self.clean_and_validate_raw_df(raw_df)

                if clean_df.empty:
                    record.status = "EMPTY"
                    record.error_message = "API returned no candles for batch"
                    overall_stats["failed_batches"] += 1
                else:
                    parquet_path = self.storage.write_partition(
                        clean_df, year, month, "nifty50"
                    )
                    record.status = "COMPLETED"
                    record.candle_count = len(clean_df)
                    record.trading_days_count = int(clean_df["timestamp"].dt.date.nunique())
                    record.first_timestamp = clean_df["timestamp"].iloc[0].isoformat()
                    record.last_timestamp = clean_df["timestamp"].iloc[-1].isoformat()
                    record.rejected_rows_count = rejected
                    record.parquet_path = str(parquet_path.relative_to(self.settings.project_root))
                    record.error_message = None

                    overall_stats["completed_batches"] += 1
                    overall_stats["total_candles"] += len(clean_df)
                    overall_stats["total_rejected"] += rejected

            except Exception as e:
                logger.error("Failed batch %s (%s to %s): %s", batch_id, batch_start, batch_end, e)
                record.status = "FAILED"
                record.error_message = str(e)
                overall_stats["failed_batches"] += 1

            self._manifest["batches"][batch_id] = asdict(record)
            self._save_manifest()

        return overall_stats
