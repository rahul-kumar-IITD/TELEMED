"""Column types."""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class UtcDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as fixed-width UTC text so lexical order is chronological."""

    impl = String(26)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime rejected; use a timezone-aware datetime")
        return value.astimezone(UTC).strftime(_FORMAT)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return datetime.strptime(str(value), _FORMAT).replace(tzinfo=UTC)
