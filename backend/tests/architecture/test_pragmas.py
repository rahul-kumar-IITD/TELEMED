"""E1-S1 AC4: every new connection reports WAL and busy_timeout >= 5000."""
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from telemed.repository.database import create_db_engine


def _pragmas(engine: Engine) -> tuple[str, int, int]:
    with engine.connect() as conn:
        mode = str(conn.execute(text("PRAGMA journal_mode")).scalar_one())
        timeout = int(conn.execute(text("PRAGMA busy_timeout")).scalar_one())
        fks = int(conn.execute(text("PRAGMA foreign_keys")).scalar_one())
    return mode, timeout, fks


@pytest.mark.ac("AC-E1-S1-4")
def test_every_new_connection_has_pragmas(engine: Engine) -> None:
    for _ in range(3):
        mode, timeout, fks = _pragmas(engine)
        assert mode == "wal"
        assert timeout >= 5000
        assert fks == 1


@pytest.mark.ac("AC-E1-S1-4")
def test_busy_timeout_floor_enforced(tmp_path: Path) -> None:
    eng = create_db_engine(str(tmp_path / "x.db"), busy_timeout_ms=10)
    try:
        assert _pragmas(eng)[1] == 5000
    finally:
        eng.dispose()
