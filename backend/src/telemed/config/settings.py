"""Typed settings loaded from the environment."""
import secrets
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_BYTES = 32
# Denylist only: this historical committed value is refused outside dev, never used as a default.
_REFUSED_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"


class Settings(BaseSettings):
    """Process settings. Field names map to upper-case env vars (PROVIDER_TIMEZONE, ...)."""

    model_config = SettingsConfigDict(extra="ignore", frozen=True, hide_input_in_errors=True)

    app_env: Literal["dev", "staging", "prod"] = "dev"
    provider_timezone: str = "UTC"
    jwt_lifetime_minutes: int = Field(default=30, ge=1)
    database_path: str = "./telemed.db"
    busy_timeout_ms: int = Field(default=10000, ge=5000)
    video_base_url: str = "https://video.example.test/visit"
    # Declared last so app_env is validated first; empty means "not supplied".
    jwt_secret: SecretStr = Field(default=SecretStr(""), validate_default=True)

    @field_validator("jwt_secret")
    @classmethod
    def _valid_secret(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        raw = value.get_secret_value()
        is_dev = info.data.get("app_env") == "dev"
        if not raw:
            if not is_dev:
                raise ValueError("JWT_SECRET is required unless APP_ENV=dev")
            return SecretStr(secrets.token_urlsafe(48))  # random per process, never fixed
        if raw == _REFUSED_JWT_SECRET and not is_dev:
            raise ValueError("JWT_SECRET must not be the published development value")
        if len(raw.encode()) < MIN_JWT_SECRET_BYTES:
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
