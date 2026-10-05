"""Typed settings loaded from the environment."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_BYTES = 32
DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"  # 49 bytes; never for prod


class Settings(BaseSettings):
    """Process settings. Field names map to upper-case env vars (PROVIDER_TIMEZONE, ...)."""

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    provider_timezone: str = "UTC"
    jwt_lifetime_minutes: int = Field(default=30, ge=1)
    database_path: str = "./telemed.db"
    busy_timeout_ms: int = Field(default=10000, ge=5000)
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    video_base_url: str = "https://video.example.test/visit"

    @field_validator("jwt_secret")
    @classmethod
    def _long_enough_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < MIN_JWT_SECRET_BYTES:
            raise ValueError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes")
        return value

    @field_validator("provider_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            raise ValueError("PROVIDER_TIMEZONE is not a known IANA timezone name") from exc
        return value


def load_settings() -> Settings:
    """Read settings from the environment; raises ValidationError naming bad variables."""
    return Settings()
