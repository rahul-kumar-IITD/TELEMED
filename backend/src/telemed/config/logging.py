"""Structured JSON logging with correlation ids. Only whitelisted fields are ever emitted."""
import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import IO, Any

NO_CORRELATION_ID = "-"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default=NO_CORRELATION_ID)

# Identifier-only fields that may be attached via `extra=`. Anything else is dropped.
ALLOWED_FIELDS = frozenset(
    {
        "user_id",
        "appointment_id",
        "version_number",
        "event_type",
        "status_code",
        "path_template",
        "method",
        "duration_ms",
        "error_class",
    }
)
_HANDLER_MARK = "_telemed_json_handler"
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")


def set_correlation_id(value: str) -> Token[str]:
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """One JSON object per line; never renders exception text, args beyond the message, or
    non-whitelisted extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        for key in ALLOWED_FIELDS:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        return json.dumps(payload, default=str)


def make_handler(stream: IO[str]) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _HANDLER_MARK, True)
    return handler


def configure_logging(stream: IO[str] | None = None, level: int = logging.INFO) -> None:
    """Route the root and uvicorn loggers through the JSON handler (idempotent)."""
    handler = make_handler(stream if stream is not None else sys.stdout)
    root = logging.getLogger()
    for existing in [h for h in root.handlers if getattr(h, _HANDLER_MARK, False)]:
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    access = logging.getLogger("uvicorn.access")  # replaced by the app's own access log line
    access.handlers.clear()
    access.propagate = False
    access.disabled = True
