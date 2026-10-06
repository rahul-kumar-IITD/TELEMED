"""E6-S1: idempotent synthetic seed data."""
import runpy
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from telemed.repository.models import DoctorProfile, Slot, User
from telemed.service import bootstrap
from telemed.service.container import Container, build_container
from telemed.service.seed_service import ADMIN_EMAIL, SeedService
from tests.conftest import FrozenClock

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed.py"
PASSWORD = "Seed-Test-Passw0rd"


@pytest.fixture
def container(
    db_path: Path, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> Container:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    return build_container(bootstrap.bootstrap(), frozen_clock)


def _seed(container: Container) -> SeedService:
    return SeedService(container.uow, container.clock, container.auth, container.doctors)


def _counts(engine: Engine) -> tuple[int, int]:
    with Session(engine) as session:
        users = session.scalar(select(func.count()).select_from(User))
        slots = session.scalar(select(func.count()).select_from(Slot))
    return int(users or 0), int(slots or 0)


@pytest.mark.ac("E6-S1-AC1")
def test_seed_creates_admin_doctors_and_patients(container: Container, engine: Engine) -> None:
    summary = _seed(container).run(PASSWORD)
    with Session(engine) as session:
        roles = list(session.scalars(select(User.role)))
        specialties = set(session.scalars(select(DoctorProfile.specialty)))
    assert roles.count("ADMIN") == 1
    assert roles.count("DOCTOR") >= 3
    assert roles.count("PATIENT") >= 5
    assert len(specialties) >= 3
    assert summary.users_created == len(roles)
    assert summary.slots_created > 0
    assert container.auth.login(ADMIN_EMAIL, PASSWORD).role.value == "ADMIN"


@pytest.mark.ac("E6-S1-AC2")
def test_seed_twice_creates_no_duplicates(container: Container, engine: Engine) -> None:
    service = _seed(container)
    service.run(PASSWORD)
    before = _counts(engine)
    second = service.run(PASSWORD)
    assert _counts(engine) == before
    assert (second.users_created, second.slots_created) == (0, 0)


@pytest.mark.ac("E6-S1-AC3")
def test_seed_emails_are_synthetic_and_slots_within_fourteen_days(
    container: Container, engine: Engine, frozen_clock: FrozenClock
) -> None:
    _seed(container).run(PASSWORD)
    now = frozen_clock.now()
    with Session(engine) as session:
        emails = list(session.scalars(select(User.email)))
        starts = list(session.scalars(select(Slot.start_time)))
    assert all(email.endswith("@example.test") for email in emails)
    assert starts
    assert all(now < start < now + timedelta(days=14) for start in starts)


@pytest.mark.ac("E6-S1-AC2")
def test_seed_script_is_runnable_and_idempotent(
    db_path: Path, engine: Engine, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    monkeypatch.setenv("SEED_PASSWORD", PASSWORD)
    for _ in range(2):
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_path(str(SCRIPT), run_name="__main__")
        assert exit_info.value.code == 0
    first = _counts(engine)
    assert first[0] == 9
    assert "seed complete" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert _counts(engine) == first
