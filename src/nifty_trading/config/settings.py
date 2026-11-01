"""Application configuration and environment settings."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Platform Environment
    platform_env: str = Field(default="development", alias="PLATFORM_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    broker_type: str = Field(default="5paisa", alias="BROKER_TYPE")
    operational_mode: str = Field(default="paper", alias="OPERATIONAL_MODE")

    # 5paisa Credentials
    fivepaisa_app_name: str = Field(default="", alias="FIVEPAISA_APP_NAME")
    fivepaisa_app_source: str = Field(default="", alias="FIVEPAISA_APP_SOURCE")
    fivepaisa_user_id: str = Field(default="", alias="FIVEPAISA_USER_ID")
    fivepaisa_password: SecretStr = Field(default=SecretStr(""), alias="FIVEPAISA_PASSWORD")
    fivepaisa_user_key: SecretStr = Field(default=SecretStr(""), alias="FIVEPAISA_USER_KEY")
    fivepaisa_encryption_key: SecretStr = Field(
        default=SecretStr(""), alias="FIVEPAISA_ENCRYPTION_KEY"
    )
    fivepaisa_client_code: str = Field(default="", alias="FIVEPAISA_CLIENT_CODE")
    fivepaisa_totp_secret: SecretStr = Field(
        default=SecretStr(""), alias="FIVEPAISA_TOTP_SECRET"
    )
    fivepaisa_pin: SecretStr = Field(default=SecretStr(""), alias="FIVEPAISA_PIN")

    # Historical Data Settings
    data_start_date: str = Field(default="2025-09-01", alias="DATA_START_DATE")
    data_end_date: str = Field(default="2026-08-31", alias="DATA_END_DATE")
    data_timeframe: str = Field(default="1m", alias="DATA_TIMEFRAME")
    data_format: str = Field(default="parquet", alias="DATA_FORMAT")
    data_compression: str = Field(default="zstd", alias="DATA_COMPRESSION")
    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")

    # Trading Execution Safeguards
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")

    # Absolute Project Paths
    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"

    def get_py5paisa_cred(self) -> dict[str, str]:
        """Construct py5paisa client credentials dictionary safely."""
        return {
            "APP_SOURCE": self.fivepaisa_app_source,
            "APP_NAME": self.fivepaisa_app_name,
            "USER_ID": self.fivepaisa_user_id,
            "PASSWORD": self.fivepaisa_password.get_secret_value(),
            "USER_KEY": self.fivepaisa_user_key.get_secret_value(),
            "ENCRYPTION_KEY": self.fivepaisa_encryption_key.get_secret_value(),
        }


# Global singleton instance
settings = Settings()
