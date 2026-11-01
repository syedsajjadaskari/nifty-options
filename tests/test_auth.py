"""Unit tests for authentication manager, token caching, and error handling."""

from unittest.mock import MagicMock, patch

import pytest

from nifty_trading.broker.auth import FivePaisaAuthManager
from nifty_trading.config.settings import Settings


def test_auth_missing_credentials():
    """Verify that clear errors are raised when credentials are missing."""
    empty_settings = Settings(
        FIVEPAISA_CLIENT_CODE="",
        FIVEPAISA_TOTP_SECRET="",
        FIVEPAISA_PIN="",
    )
    manager = FivePaisaAuthManager(empty_settings)
    with pytest.raises(ValueError, match="FIVEPAISA_CLIENT_CODE is not configured"):
        manager.create_authenticated_client(force_refresh=True)


def test_auth_invalid_totp_secret():
    """Verify that invalid base32 TOTP secrets raise clear errors."""
    bad_settings = Settings(
        FIVEPAISA_CLIENT_CODE="12345678",
        FIVEPAISA_TOTP_SECRET="invalid_non_base32_!@#$",
        FIVEPAISA_PIN="123456",
    )
    manager = FivePaisaAuthManager(bad_settings)
    with pytest.raises(ValueError, match="Failed to generate TOTP"):
        manager.create_authenticated_client(force_refresh=True)


@patch("nifty_trading.broker.auth.FivePaisaClient")
def test_auth_broker_rejection(mock_client_cls):
    """Verify handling when broker returns no token."""
    mock_instance = MagicMock()
    mock_instance.get_totp_session.return_value = None
    mock_instance.access_token = ""
    mock_client_cls.return_value = mock_instance

    valid_settings = Settings(
        FIVEPAISA_CLIENT_CODE="12345678",
        FIVEPAISA_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        FIVEPAISA_PIN="123456",
    )
    manager = FivePaisaAuthManager(valid_settings)
    with pytest.raises(RuntimeError, match="Authentication failed: 5paisa did not return a valid access token"):
        manager.create_authenticated_client(force_refresh=True)


@patch("nifty_trading.broker.auth.FivePaisaClient")
def test_verify_connection_sanitized_output(mock_client_cls):
    """Verify sanitized AuthResult output structure and masking."""
    mock_instance = MagicMock()
    mock_instance.get_totp_session.return_value = "dummy_token"
    mock_instance.access_token = "dummy_token"
    mock_instance.margin.return_value = [{"EquityMargin": 100000.0}]
    mock_client_cls.return_value = mock_instance

    settings_obj = Settings(
        FIVEPAISA_CLIENT_CODE="54574190",
        FIVEPAISA_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        FIVEPAISA_PIN="123456",
        OPERATIONAL_MODE="paper",
        ENABLE_LIVE_TRADING=False,
    )
    manager = FivePaisaAuthManager(settings_obj)
    # Bypass cached token for test
    manager._load_cached_token = MagicMock(return_value=None)
    manager._save_cached_token = MagicMock()

    result = manager.verify_connection()

    assert result.auth_success is True
    assert result.readonly_api_success is True
    assert result.operational_mode == "PAPER"
    assert result.live_orders_enabled is False
    assert result.client_code == "***190"
    assert "dummy_token" not in str(result)
