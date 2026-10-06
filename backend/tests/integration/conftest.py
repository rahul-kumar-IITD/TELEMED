"""Shared fixtures for the reschedule / lifecycle / queue integration tests (group H)."""
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from telemed.api import deps
from telemed.api.app import create_app
from telemed.repository.models import Appointment, AppointmentEvent, Slot, User
from telemed.service import security
from telemed.types.enums import Role
from tests.conftest import FrozenClock, SpyPayment

PASSWORD = "Passw0rd!"
NOW = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
TEMPLATES = [
    {"weekday": d, "start_time": "09:00", "end_time": "11:00", "slot_length_minutes": 30}
    for d in range(7)
]
Headers = dict[str, str]
Doctor = tuple[int, Headers]


@pytest.fixture
def provider_tz() -> str:
    return "UTC"


@pytest.fixture
def payment() -> SpyPayment:
    return SpyPayment()


@pytest.fixture
def app(
    db_path: Path, frozen_clock: FrozenClock, payment: SpyPayment, provider_tz: str,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", provider_tz)
    application = create_app(clock=frozen_clock)
    application.dependency_overrides[deps.get_payment_service] = lambda: payment
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def login(client: TestClient, email: str) -> Headers:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register(client: TestClient, email: str) -> Headers:
    client.post("/api/auth/register", json={
        "email": email, "password": PASSWORD, "full_name": "Pat Ient", "age": 30,
        "gender": "MALE", "phone": "1"})
    return login(client, email)


@pytest.fixture
def admin(client: TestClient, engine: Engine) -> Headers:
    with Session(engine) as session:
        session.add(User(email="admin@example.test", password_hash=security.hash_password(PASSWORD),
                         role=Role.ADMIN.value, active=1, created_at=NOW, updated_at=NOW))
        session.commit()
    return login(client, "admin@example.test")


def onboard(client: TestClient, admin: Headers, email: str) -> Doctor:
    response = client.post("/api/admin/doctors", headers=admin, json={
        "email": email, "initial_password": PASSWORD, "full_name": "Dr Rao",
        "specialty": "Cardiology", "languages": ["en"], "fee": "500",
        "availability_templates": TEMPLATES})
    assert response.status_code == 201
    return int(response.json()["doctor_id"]), login(client, email)


@pytest.fixture
def doctor(client: TestClient, admin: Headers) -> Doctor:
    return onboard(client, admin, "d@example.test")


@pytest.fixture
def patient(client: TestClient) -> Headers:
    return register(client, "p@example.test")


def slot_ids(engine: Engine, doctor_id: int, count: int) -> list[int]:
    """The doctor's first `count` AVAILABLE slots, oldest first."""
    with Session(engine) as session:
        return list(session.scalars(
            select(Slot.slot_id).where(Slot.doctor_id == doctor_id, Slot.status == "AVAILABLE")
            .order_by(Slot.start_time).limit(count)))


def set_slot_start(engine: Engine, slot_id: int, start: datetime) -> None:
    with Session(engine) as session:
        session.execute(update(Slot).where(Slot.slot_id == slot_id).values(
            start_time=start, end_time=start + timedelta(minutes=30)))
        session.commit()


def book(client: TestClient, patient: Headers, slot_id: int) -> int:
    response = client.post("/api/appointments", headers=patient, json={"slot_id": slot_id})
    assert response.status_code == 201
    return int(response.json()["appointment_id"])


def book_at(
    client: TestClient, engine: Engine, doctor_id: int, patient: Headers, start: datetime
) -> tuple[int, int]:
    """Book the doctor's first open slot, then move it to `start`; returns (appt, slot)."""
    slot_id = slot_ids(engine, doctor_id, 1)[0]
    appt = book(client, patient, slot_id)
    set_slot_start(engine, slot_id, start)
    return appt, slot_id


def set_status(engine: Engine, appointment_id: int, status: str) -> None:
    with Session(engine) as session:
        session.execute(update(Appointment).where(Appointment.appointment_id == appointment_id)
                        .values(status=status))
        session.commit()


def slot_status(engine: Engine, slot_id: int) -> str:
    with Session(engine) as session:
        row = session.get(Slot, slot_id)
        assert row is not None
        return row.status


def appt_row(engine: Engine, appointment_id: int) -> Appointment:
    with Session(engine) as session:
        row = session.get(Appointment, appointment_id)
        assert row is not None
        session.expunge(row)
        return row


def events(engine: Engine, appointment_id: int) -> list[AppointmentEvent]:
    with Session(engine) as session:
        rows = list(session.scalars(
            select(AppointmentEvent).where(AppointmentEvent.appointment_id == appointment_id)
            .order_by(AppointmentEvent.event_id)))
        session.expunge_all()
        return rows
