"""Unit tests for configuration, paths, and credential safety."""

from nifty_trading.config.settings import Settings


def test_settings_credential_masking():
    """Ensure secret fields never leak in string representation."""
    s = Settings(
        FIVEPAISA_PASSWORD="secret_password_123",
        FIVEPAISA_PIN="123456",
        FIVEPAISA_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )

    repr_str = repr(s)
    str_val = str(s)

    assert "secret_password_123" not in repr_str
    assert "secret_password_123" not in str_val
    assert "123456" not in repr_str
    assert "JBSWY3DPEHPK3PXP" not in repr_str
    assert "**********" in repr_str


def test_py5paisa_cred_dict():
    """Verify that credentials dictionary is constructed correctly."""
    s = Settings(
        FIVEPAISA_APP_NAME="test_app",
        FIVEPAISA_APP_SOURCE="test_src",
        FIVEPAISA_USER_ID="test_user",
        FIVEPAISA_PASSWORD="test_password",
        FIVEPAISA_USER_KEY="test_key",
        FIVEPAISA_ENCRYPTION_KEY="test_enc",
    )
    cred = s.get_py5paisa_cred()
    assert cred["APP_NAME"] == "test_app"
    assert cred["APP_SOURCE"] == "test_src"
    assert cred["USER_ID"] == "test_user"
    assert cred["PASSWORD"] == "test_password"
    assert cred["USER_KEY"] == "test_key"
    assert cred["ENCRYPTION_KEY"] == "test_enc"


def test_project_paths():
    """Verify project directory paths are anchored to project root."""
    s = Settings()
    assert s.project_root.exists()
    assert s.data_dir == s.project_root / "data"
    assert s.metadata_dir == s.data_dir / "metadata"
    assert s.processed_data_dir == s.data_dir / "processed"
