"""Authentication and session management for 5paisa Developer API."""

import importlib.metadata
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pyotp
from loguru import logger as loguru_logger
from py5paisa import FivePaisaClient

from nifty_trading.config.constants import IST
from nifty_trading.config.settings import Settings, settings

# Suppress py5paisa internal token logging to ensure credentials/tokens never leak
loguru_logger.disable("py5paisa")

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Sanitized authentication verification result."""

    sdk_version: str
    auth_success: bool
    readonly_api_success: bool
    timestamp_ist: str
    operational_mode: str
    live_orders_enabled: bool
    client_code: str
    error_message: str | None = None
    account_summary: dict[str, Any] | None = None


def get_sdk_version() -> str:
    """Retrieve installed py5paisa SDK version."""
    try:
        return importlib.metadata.version("py5paisa")
    except Exception:
        return "unknown"


class FivePaisaAuthManager:
    """Handles 5paisa TOTP session creation, caching, and read-only connectivity checks."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self.sdk_version = get_sdk_version()
        self._client: FivePaisaClient | None = None
        self._token_file = self.settings.project_root / ".session_token.json"

    def _load_cached_token(self) -> dict[str, Any] | None:
        """Load session token cached on local disk if still valid today."""
        if not self._token_file.exists():
            return None
        try:
            with open(self._token_file, "r") as f:
                data = json.load(f)
            cached_date = data.get("date")
            today_str = datetime.now(IST).strftime("%Y-%m-%d")
            # 5paisa tokens expire daily
            if cached_date == today_str and data.get("access_token") and data.get("client_code"):
                return data
        except Exception as e:
            logger.debug("Failed reading cached token: %s", e)
        return None

    def _save_cached_token(self, access_token: str, client_code: str) -> None:
        """Cache session token with restricted file permissions."""
        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        try:
            payload = {
                "date": today_str,
                "access_token": access_token,
                "client_code": client_code,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._token_file, "w") as f:
                json.dump(payload, f)
            self._token_file.chmod(0o600)
        except Exception as e:
            logger.warning("Could not persist session token cache: %s", e)

    def create_authenticated_client(self, force_refresh: bool = False) -> FivePaisaClient:
        """Authenticate with 5paisa using cached token or fresh TOTP session workflow."""
        cred = self.settings.get_py5paisa_cred()

        client_code = self.settings.fivepaisa_client_code
        totp_secret = self.settings.fivepaisa_totp_secret.get_secret_value()
        pin = self.settings.fivepaisa_pin.get_secret_value()

        if not client_code:
            raise ValueError("FIVEPAISA_CLIENT_CODE is not configured.")

        # 1. Check cached session token first
        if not force_refresh:
            cached = self._load_cached_token()
            if cached and cached.get("client_code") == client_code:
                client = FivePaisaClient(cred=cred)
                client.set_access_token(cached["access_token"], cached["client_code"])
                # Quick verification of cached token validity
                try:
                    margin_data = client.margin()
                    if margin_data is not None:
                        self._client = client
                        return client
                except Exception:
                    logger.info("Cached token invalid or expired. Refreshing via TOTP.")

        # 2. Negotiate fresh TOTP session
        if not totp_secret:
            raise ValueError("FIVEPAISA_TOTP_SECRET is not configured.")
        if not pin:
            raise ValueError("FIVEPAISA_PIN is not configured.")

        client = FivePaisaClient(cred=cred)

        try:
            totp = pyotp.TOTP(totp_secret)
            current_totp = totp.now()
        except Exception as e:
            raise ValueError(f"Failed to generate TOTP from secret: {e}") from e

        try:
            token = client.get_totp_session(client_code=client_code, totp=current_totp, pin=pin)
        except Exception as e:
            raise RuntimeError(f"Error during 5paisa TOTP session negotiation: {e}") from e

        if not token or not client.access_token:
            raise RuntimeError(
                "Authentication failed: 5paisa did not return a valid access token. "
                "Check client code, TOTP secret, PIN, and API keys."
            )

        self._save_cached_token(client.access_token, client_code)
        self._client = client
        return client

    def verify_connection(self) -> AuthResult:
        """Run connection verification and execute a safe read-only API request."""
        now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")
        masked_code = (
            f"***{self.settings.fivepaisa_client_code[-3:]}"
            if len(self.settings.fivepaisa_client_code) > 3
            else "***"
        )

        try:
            client = self.create_authenticated_client()
            auth_success = bool(client.access_token)
        except Exception as e:
            logger.error("Authentication check failed: %s", e)
            return AuthResult(
                sdk_version=self.sdk_version,
                auth_success=False,
                readonly_api_success=False,
                timestamp_ist=now_ist,
                operational_mode=self.settings.operational_mode.upper(),
                live_orders_enabled=self.settings.enable_live_trading,
                client_code=masked_code,
                error_message=str(e),
            )

        # Verify read-only endpoint (Margin request)
        readonly_success = False
        summary = None
        err_msg = None

        try:
            margin_data = client.margin()
            if margin_data is not None:
                readonly_success = True
                # Extract non-sensitive high-level summary if available
                if isinstance(margin_data, list) and len(margin_data) > 0:
                    summary = {"records_returned": len(margin_data)}
                elif isinstance(margin_data, dict):
                    summary = {"status": "ok", "keys": list(margin_data.keys())}
                else:
                    summary = {"response_type": type(margin_data).__name__}
            else:
                err_msg = "Read-only margin request returned None."
        except Exception as e:
            err_msg = f"Read-only API call failed: {e}"
            logger.error("Read-only verification failed: %s", e)

        return AuthResult(
            sdk_version=self.sdk_version,
            auth_success=auth_success,
            readonly_api_success=readonly_success,
            timestamp_ist=now_ist,
            operational_mode=self.settings.operational_mode.upper(),
            live_orders_enabled=self.settings.enable_live_trading,
            client_code=masked_code,
            error_message=err_msg,
            account_summary=summary,
        )
