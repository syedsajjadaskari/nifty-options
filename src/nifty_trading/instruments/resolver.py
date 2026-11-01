"""Instrument resolution and verification for NIFTY 50 spot index."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nifty_trading.config.settings import Settings, settings
from nifty_trading.instruments.master import InstrumentMasterManager

logger = logging.getLogger(__name__)


@dataclass
class InstrumentMetadata:
    """Resolved instrument metadata model."""

    symbol: str
    full_name: str
    exchange: str
    exchange_segment: str
    scrip_code: int
    scrip_type: str
    series: str
    tick_size: float
    lot_size: int
    is_index: bool
    verified_at_utc: str
    historical_api_verified: bool
    source_master_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InstrumentResolver:
    """Resolves and verifies tradeable and historical instruments from 5paisa scrip master."""

    def __init__(
        self,
        app_settings: Settings = settings,
        master_manager: InstrumentMasterManager | None = None,
    ):
        self.settings = app_settings
        self.master_manager = master_manager or InstrumentMasterManager(app_settings)
        self.metadata_dir = self.settings.metadata_dir

    def resolve_nifty50_index(self, force_refresh: bool = False) -> InstrumentMetadata:
        """Find and verify NIFTY 50 spot index from 5paisa instrument master.

        Strictly avoids ETFs (e.g. NIFTYBEES), futures, and options.
        """
        json_path = self.metadata_dir / "nifty50_instrument.json"
        if json_path.exists() and not force_refresh:
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
                return InstrumentMetadata(**data)
            except Exception as e:
                logger.warning("Could not read cached instrument metadata: %s", e)

        df = self.master_manager.load_master_dataframe(force_download=force_refresh)

        # Filter strictly for NSE Cash/Index segment
        # In 5paisa scrip master:
        # Exch == 'N', ExchType == 'C'
        # ScripCode 999920000 is NIFTY index
        # Name == 'NIFTY'
        candidates = df[
            (df["Exch"] == "N")
            & (df["ExchType"] == "C")
            & (df["ScripCode"].astype(str) == "999920000")
        ]

        if candidates.empty:
            # Fallback search if scrip code differs in future master files
            candidates = df[
                (df["Exch"] == "N")
                & (df["ExchType"] == "C")
                & (df["Name"].str.upper() == "NIFTY")
                & (df["ScripCode"].astype(str).str.startswith("9999"))
            ]

        if candidates.empty:
            raise LookupError(
                "NIFTY 50 spot index could not be located in 5paisa instrument master. "
                "Ensure ScripMaster was downloaded correctly."
            )

        row = candidates.iloc[0]

        # Verify not an ETF, future, or option
        full_name = str(row.get("FullName", "")).strip()
        series = str(row.get("Series", "")).strip()
        scrip_type = str(row.get("ScripType", "")).strip()
        scrip_code = int(row["ScripCode"])

        if "ETF" in full_name.upper():
            raise ValueError(f"Resolved instrument appears to be an ETF: {full_name}")

        tick_size = float(row.get("TickSize", 0.05) or 0.05)
        lot_size = int(row.get("LotSize", 1) or 1)

        metadata = InstrumentMetadata(
            symbol=str(row.get("Name", "NIFTY")).strip(),
            full_name=full_name or "NIFTY 50",
            exchange=str(row.get("Exch", "N")).strip(),
            exchange_segment=str(row.get("ExchType", "C")).strip(),
            scrip_code=scrip_code,
            scrip_type=scrip_type,
            series=series,
            tick_size=tick_size,
            lot_size=lot_size,
            is_index=True,
            verified_at_utc=datetime.now(timezone.utc).isoformat(),
            historical_api_verified=False,
            source_master_file=str(self.master_manager.master_csv_path),
        )

        self.save_metadata(metadata)
        return metadata

    def save_metadata(self, metadata: InstrumentMetadata) -> Path:
        """Persist instrument metadata to JSON under data/metadata/."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.metadata_dir / "nifty50_instrument.json"
        with open(out_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        return out_path
