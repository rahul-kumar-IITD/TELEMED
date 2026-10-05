"""Composition root: hands settings, logging and DB-error classification to the API layer."""
import logging
import sqlite3
from contextvars import Token
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError

from telemed.config import logging as app_logging
from telemed.config.settings import Settings, load_settings

_LOCK_MARKERS = ("database is locked", "database table is locked")
_logger = logging.getLogger("telemed.app")


@dataclass(frozen=True)
class Runtime:
    """Process-wide configuration values exposed to the API layer."""

    provider_timezone: str
    jwt_lifetime_minutes: int
    database_path: str
    busy_timeout_ms: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "Runtime":
        return cls(
            provider_timezone=settings.provider_timezone,
            jwt_lifetime_minutes=settings.jwt_lifetime_minutes,
            database_path=settings.database_path,
            busy_timeout_ms=settings.busy_timeout_ms,
        )


def bootstrap() -> Runtime:
    """Load and validate settings (aborts on invalid values) and configure JSON logging."""
    runtime = Runtime.from_settings(load_settings())
    app_logging.configure_logging()
    return runtime


def bind_correlation_id(value: str) -> Token[str]:
    return app_logging.set_correlation_id(value)


def unbind_correlation_id(token: Token[str]) -> None:
    app_logging.reset_correlation_id(token)


def log_event(event: str, **fields: object) -> None:
    """Emit one structured log line; only whitelisted identifier fields are rendered."""
    _logger.info(event, extra=fields)


def is_lock_timeout(exc: BaseException) -> bool:
    """True if `exc` is a SQLite lock/busy timeout."""
    if isinstance(exc, OperationalError):
        return is_lock_timeout(exc.orig) if exc.orig is not None else False
    if isinstance(exc, sqlite3.OperationalError):
        return any(marker in str(exc) for marker in _LOCK_MARKERS)
    return False
