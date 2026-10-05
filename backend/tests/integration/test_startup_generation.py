"""E2-S1 AC3/AC5: app startup (lifespan) tops up the 14-day slot window idempotently."""
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.repository.models import Slot
from tests.conftest import FrozenClock
from tests.factories import add_doctor

EVERY_DAY = [(day, "09:00", "10:00", 60) for day in range(7)]


@pytest.fixture(autouse=True)
def env(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))


def _start_and_stop(clock: FrozenClock) -> None:
    with TestClient(create_app(clock=clock)) as client:
        assert client.get("/health").status_code == 200


def _count(engine: Engine) -> int:
    with Session(engine) as session:
        return int(session.scalar(select(func.count()).select_from(Slot)) or 0)


@pytest.mark.ac("AC-E2-S1-5")
def test_startup_creates_slots_and_restart_adds_only_new_days(
    engine: Engine, frozen_clock: FrozenClock
) -> None:
    add_doctor(engine, "d1@example.test", EVERY_DAY)
    _start_and_stop(frozen_clock)
    first = _count(engine)
    assert first == 14  # one 09:00 slot per day, Oct 6 09:00 .. Oct 19 09:00
    _start_and_stop(frozen_clock)
    assert _count(engine) == first  # AC3: restart without clock change adds nothing
    frozen_clock.advance(timedelta(days=5))
    _start_and_stop(frozen_clock)
    assert _count(engine) == first + 5  # Oct 20 .. Oct 24
    with Session(engine) as session:
        dupes = session.execute(
            text("SELECT 1 FROM slots GROUP BY doctor_id, start_time HAVING COUNT(*) > 1")
        ).all()
        assert dupes == []


def test_startup_survives_generation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_clock: FrozenClock
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "unmigrated.db"))  # no tables
    with TestClient(create_app(clock=frozen_clock)) as client:
        assert client.get("/health").status_code == 200
