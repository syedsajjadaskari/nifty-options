"""Broker client wrapper for 5paisa with safeguards, rate limiting, and retries."""

import logging
from typing import Any

import pandas as pd
from py5paisa import FivePaisaClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from nifty_trading.broker.auth import FivePaisaAuthManager
from nifty_trading.broker.rate_limiter import RateLimiter
from nifty_trading.config.settings import Settings, settings

logger = logging.getLogger(__name__)


class BrokerClient:
    """Safeguarded broker client for 5paisa with retry logic and rate limits."""

    def __init__(
        self,
        app_settings: Settings = settings,
        auth_manager: FivePaisaAuthManager | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.settings = app_settings
        self.auth_manager = auth_manager or FivePaisaAuthManager(app_settings)
        self.rate_limiter = rate_limiter or RateLimiter()
        self._raw_client: FivePaisaClient | None = None

    @property
    def raw_client(self) -> FivePaisaClient:
        """Obtain or authenticate underlying py5paisa client."""
        if self._raw_client is None:
            self._raw_client = self.auth_manager.create_authenticated_client()
        return self._raw_client

    def ensure_authenticated(self) -> FivePaisaClient:
        """Explicitly ensure the client is authenticated."""
        return self.raw_client

    # Safe Read-Only Broker Endpoints
    def get_margin(self) -> Any:
        """Fetch margin details (read-only)."""
        self.rate_limiter.wait()
        return self.raw_client.margin()

    def get_holdings(self) -> Any:
        """Fetch current holdings (read-only)."""
        self.rate_limiter.wait()
        return self.raw_client.holdings()

    def get_positions(self) -> Any:
        """Fetch open positions (read-only)."""
        self.rate_limiter.wait()
        return self.raw_client.positions()

    def get_scrips(self) -> pd.DataFrame:
        """Fetch broker instrument master."""
        self.rate_limiter.wait()
        return self.raw_client.get_scrips()

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1.0, max=10.0),
        reraise=True,
    )
    def fetch_historical_candles(
        self,
        exch: str,
        exchange_segment: str,
        scrip_code: int,
        timeframe: str,
        from_date: str,
        to_date: str,
    ) -> pd.DataFrame:
        """Fetch historical candle dataframe with rate limiting and exponential retries.

        Args:
            exch: Exchange code ('N', 'B', 'M')
            exchange_segment: Segment ('C', 'D', 'U')
            scrip_code: Numeric instrument identifier
            timeframe: Candle interval ('1m', '5m', '15m', '60m', '1d')
            from_date: Start date string (YYYY-MM-DD)
            to_date: End date string (YYYY-MM-DD)
        """
        self.rate_limiter.wait()
        logger.debug(
            "Fetching candles: exch=%s segment=%s scrip=%s tf=%s from=%s to=%s",
            exch,
            exchange_segment,
            scrip_code,
            timeframe,
            from_date,
            to_date,
        )
        try:
            df = self.raw_client.historical_data(
                Exch=exch,
                ExchangeSegment=exchange_segment,
                ScripCode=scrip_code,
                time=timeframe,
                From=from_date,
                To=to_date,
            )
        except Exception as e:
            logger.error("Error invoking py5paisa historical_data: %s", e)
            raise

        if isinstance(df, str):
            # py5paisa returns string on validation/API error
            raise ValueError(f"5paisa historical API returned error string: {df}")

        if df is None:
            return pd.DataFrame()

        return df

    # Order Safeguards — STRICTLY DISABLED IN PHASE 1
    def place_order(self, *args, **kwargs):
        raise PermissionError(
            "CRITICAL: Order placement is disabled in Phase 1 (ENABLE_LIVE_TRADING=false)."
        )

    def modify_order(self, *args, **kwargs):
        raise PermissionError(
            "CRITICAL: Order modification is disabled in Phase 1 (ENABLE_LIVE_TRADING=false)."
        )

    def cancel_order(self, *args, **kwargs):
        raise PermissionError(
            "CRITICAL: Order cancellation is disabled in Phase 1 (ENABLE_LIVE_TRADING=false)."
        )

    def squareoff_all(self, *args, **kwargs):
        raise PermissionError(
            "CRITICAL: Order squareoff is disabled in Phase 1 (ENABLE_LIVE_TRADING=false)."
        )
