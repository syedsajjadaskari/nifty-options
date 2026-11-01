"""5paisa Instrument Master downloader and cache manager."""

import logging
from pathlib import Path

import pandas as pd
import requests

from nifty_trading.config.constants import FIVEPAISA_SCRIP_MASTER_URL
from nifty_trading.config.settings import Settings, settings

logger = logging.getLogger(__name__)


class InstrumentMasterManager:
    """Manages downloading, caching, and querying the 5paisa Scrip Master."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self.metadata_dir = self.settings.metadata_dir
        self.master_csv_path = self.metadata_dir / "scrip_master.csv"

    def download_master(self, force: bool = False, timeout_seconds: int = 60) -> Path:
        """Download latest scrip master CSV from 5paisa and cache locally."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        if self.master_csv_path.exists() and not force:
            # Check size to ensure file is not empty or corrupted
            if self.master_csv_path.stat().st_size > 1_000_000:
                logger.info(
                    "Using existing cached scrip master: %s (size: %d bytes)",
                    self.master_csv_path,
                    self.master_csv_path.stat().st_size,
                )
                return self.master_csv_path

        logger.info("Downloading 5paisa Scrip Master from %s ...", FIVEPAISA_SCRIP_MASTER_URL)
        resp = requests.get(FIVEPAISA_SCRIP_MASTER_URL, timeout=timeout_seconds, stream=True)
        resp.raise_for_status()

        temp_path = self.master_csv_path.with_suffix(".csv.tmp")
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        temp_path.replace(self.master_csv_path)
        logger.info(
            "Scrip master successfully downloaded and cached to %s (size: %d bytes)",
            self.master_csv_path,
            self.master_csv_path.stat().st_size,
        )
        return self.master_csv_path

    def load_master_dataframe(self, force_download: bool = False) -> pd.DataFrame:
        """Load scrip master CSV into a pandas DataFrame."""
        csv_path = self.download_master(force=force_download)
        df = pd.read_csv(csv_path, low_memory=False)
        return df
