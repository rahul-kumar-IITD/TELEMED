"""Typed settings loaded from the environment."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process settings. Field names map to upper-case env vars (PROVIDER_TIMEZONE, ...)."""

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    provider_timezone: str = "UTC"
    jwt_lifetime_minutes: int = Field(default=30, ge=1)
    database_path: str = "./telemed.db"
    busy_timeout_ms: int = Field(default=10000, ge=5000)

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
