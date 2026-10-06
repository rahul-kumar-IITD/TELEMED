"""Shared fixtures: a migrated temporary SQLite database per test."""
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Engine

from telemed.api import deps
from telemed.api.app import create_app
from telemed.repository.database import create_db_engine
from telemed.types.enums import EventType
from telemed.types.ids import AppointmentId

BACKEND = Path(__file__).resolve().parents[1]


def migrate(db_path: Path) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    migrate(path)
    return path


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    eng = create_db_engine(str(db_path))
    yield eng
    eng.dispose()


class FrozenClock:
    """Deterministic injectable clock."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock(datetime(2026, 10, 6, 0, 0, tzinfo=UTC))  # a Tuesday


class SpyVideo:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def join_url(self, appointment_id: AppointmentId) -> str:
        self.calls.append(("join_url", appointment_id))
        return f"spy://{appointment_id}"


class SpyPayment:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def charge(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        self.calls.append(("charge", appointment_id, amount))
        return "spy-charge"

    def refund(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        self.calls.append(("refund", appointment_id, amount))
        return "spy-refund"


class SpyPrescription:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def issue(self, appointment_id: AppointmentId) -> str:
        self.calls.append(("issue", appointment_id))
        return "spy-rx"


class SpyNotification:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def notify(self, appointment_id: AppointmentId, event_type: EventType) -> None:
        self.calls.append(("notify", appointment_id, event_type))


@dataclass
class Spies:
    video: SpyVideo
    payment: SpyPayment
    prescription: SpyPrescription
    notification: SpyNotification


@pytest.fixture
def spies() -> Spies:
    return Spies(SpyVideo(), SpyPayment(), SpyPrescription(), SpyNotification())


@pytest.fixture
def app_with_spies(spies: Spies) -> FastAPI:
    """A real app whose four integration providers are overridden by recording spies."""
    app = create_app()
    app.dependency_overrides[deps.get_video_service] = lambda: spies.video
    app.dependency_overrides[deps.get_payment_service] = lambda: spies.payment
    app.dependency_overrides[deps.get_prescription_service] = lambda: spies.prescription
    app.dependency_overrides[deps.get_notification_service] = lambda: spies.notification
    return app


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Enforce the domain-layer coverage threshold after pytest-cov has finished."""
    from tests.coverage_gate import enforce

    enforce(session)
