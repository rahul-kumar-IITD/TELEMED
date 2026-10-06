"""Small unit checks: UtcDateTime null handling and trigger DDL matching the migration."""
from datetime import UTC, datetime
from pathlib import Path

from telemed.repository.triggers import all_trigger_ddl
from telemed.repository.types import UtcDateTime

ROOT = Path(__file__).resolve().parents[2]


def test_utc_datetime_none_passthrough_and_round_trip() -> None:
    column = UtcDateTime()
    assert column.process_bind_param(None, None) is None  # type: ignore[arg-type]
    assert column.process_result_value(None, None) is None  # type: ignore[arg-type]
    value = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    stored = column.process_bind_param(value, None)  # type: ignore[arg-type]
    assert stored == "2026-10-05 10:00:00.000000"
    assert column.process_result_value(stored, None) == value  # type: ignore[arg-type]


def test_trigger_ddl_matches_initial_migration() -> None:
    migration = (ROOT / "alembic" / "versions" / "0001_initial_schema.py").read_text(
        encoding="utf-8"
    )
    for statement in all_trigger_ddl():
        assert statement in migration
