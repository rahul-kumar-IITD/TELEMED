"""E3-S3: patient/doctor cancellation (API-24)."""
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
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
def payment() -> SpyPayment:
    return SpyPayment()


@pytest.fixture
def app(
    db_path: Path, frozen_clock: FrozenClock, payment: SpyPayment,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    application = create_app(clock=frozen_clock)
    application.dependency_overrides[deps.get_payment_service] = lambda: payment
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, email: str) -> Headers:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _register(client: TestClient, email: str) -> Headers:
    client.post("/api/auth/register", json={
        "email": email, "password": PASSWORD, "full_name": "Pat Ient", "age": 30,
        "gender": "MALE", "phone": "1"})
    return _login(client, email)


@pytest.fixture
def admin(client: TestClient, engine: Engine) -> Headers:
    with Session(engine) as session:
        session.add(User(email="admin@example.test", password_hash=security.hash_password(PASSWORD),
                         role=Role.ADMIN.value, active=1, created_at=NOW, updated_at=NOW))
        session.commit()
    return _login(client, "admin@example.test")


def _onboard(client: TestClient, admin: Headers, email: str) -> Doctor:
    response = client.post("/api/admin/doctors", headers=admin, json={
        "email": email, "initial_password": PASSWORD, "full_name": "Dr Rao",
        "specialty": "Cardiology", "languages": ["en"], "fee": "500",
        "availability_templates": TEMPLATES})
    assert response.status_code == 201
    return int(response.json()["doctor_id"]), _login(client, email)


@pytest.fixture
def doctor(client: TestClient, admin: Headers) -> Doctor:
    return _onboard(client, admin, "d@example.test")


@pytest.fixture
def patient(client: TestClient) -> Headers:
    return _register(client, "p@example.test")


def _book_at(
    client: TestClient, engine: Engine, doctor_id: int, patient: Headers, start: datetime
) -> tuple[int, int]:
    """Book the doctor's first slot, then move it to `start`; returns (appointment, slot)."""
    with Session(engine) as session:
        slot_id = int(session.scalars(
            select(Slot.slot_id).where(Slot.doctor_id == doctor_id).order_by(Slot.start_time)
        ).first() or 0)
    response = client.post("/api/appointments", headers=patient, json={"slot_id": slot_id})
    assert response.status_code == 201
    with Session(engine) as session:
        session.execute(update(Slot).where(Slot.slot_id == slot_id).values(
            start_time=start, end_time=start + timedelta(minutes=30)))
        session.commit()
    return int(response.json()["appointment_id"]), slot_id


def _slot_status(engine: Engine, slot_id: int) -> str:
    with Session(engine) as session:
        row = session.get(Slot, slot_id)
        assert row is not None
        return row.status


def _appt_status(engine: Engine, appointment_id: int) -> str:
    with Session(engine) as session:
        row = session.get(Appointment, appointment_id)
        assert row is not None
        return row.status


def _events(engine: Engine, appointment_id: int) -> list[AppointmentEvent]:
    with Session(engine) as session:
        return list(session.scalars(
            select(AppointmentEvent).where(AppointmentEvent.appointment_id == appointment_id)
            .order_by(AppointmentEvent.event_id)))


def _cancel(client: TestClient, headers: Headers | None, appointment_id: int) -> Response:
    return client.post(f"/api/appointments/{appointment_id}/cancel", headers=headers or {})


@pytest.mark.ac("E3-S3-AC1")
def test_patient_cancel_at_exactly_sixty_minutes(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment,
) -> None:
    appt, slot = _book_at(client, engine, doctor[0], patient, NOW + timedelta(minutes=60))
    response = _cancel(client, patient, appt)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCELLED"
    assert body["allowed_actions"] == []
    assert body["join_url"] is None
    assert body["patient"]["full_name"] == "Pat Ient"
    assert _appt_status(engine, appt) == "CANCELLED"
    assert _slot_status(engine, slot) == "AVAILABLE"
    cancelled = [e for e in _events(engine, appt) if e.event_type == "CANCELLED"]
    assert len(cancelled) == 1
    assert cancelled[0].actor_role == "PATIENT"
    assert cancelled[0].from_status == "BOOKED"
    assert [c[0] for c in payment.calls] == ["charge", "refund"]


@pytest.mark.ac("E3-S3-AC2")
@pytest.mark.parametrize("delta", [timedelta(minutes=59, seconds=59), timedelta(minutes=-5)])
def test_patient_cancel_inside_window_or_after_start_is_409(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment,
    delta: timedelta,
) -> None:
    appt, slot = _book_at(client, engine, doctor[0], patient, NOW + delta)
    response = _cancel(client, patient, appt)
    assert response.status_code == 409
    assert response.json()["code"] == "CHANGE_WINDOW_CLOSED"
    assert _appt_status(engine, appt) == "BOOKED"
    assert _slot_status(engine, slot) == "BOOKED"
    assert [e.event_type for e in _events(engine, appt)] == ["BOOKED"]
    assert [c[0] for c in payment.calls] == ["charge"]


@pytest.mark.ac("E3-S3-AC3")
def test_other_patient_gets_404_and_nothing_changes(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment,
) -> None:
    appt, _ = _book_at(client, engine, doctor[0], patient, NOW + timedelta(hours=5))
    other = _register(client, "q@example.test")
    assert _cancel(client, other, appt).status_code == 404
    assert _appt_status(engine, appt) == "BOOKED"
    assert len(payment.calls) == 1


@pytest.mark.ac("E3-S3-AC4")
def test_doctor_cancel_blocks_slot_and_records_doctor_role(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment,
) -> None:
    appt, slot = _book_at(client, engine, doctor[0], patient, NOW + timedelta(minutes=10))
    response = _cancel(client, doctor[1], appt)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert _slot_status(engine, slot) == "BLOCKED"
    cancelled = [e for e in _events(engine, appt) if e.event_type == "CANCELLED"]
    assert [e.actor_role for e in cancelled] == ["DOCTOR"]
    assert [c[0] for c in payment.calls] == ["charge", "refund"]


@pytest.mark.ac("E3-S3-AC4")
def test_other_doctor_404_admin_403_anonymous_401_unknown_404(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers,
) -> None:
    appt, _ = _book_at(client, engine, doctor[0], patient, NOW + timedelta(hours=3))
    _, other_doctor = _onboard(client, admin, "d2@example.test")
    assert _cancel(client, other_doctor, appt).status_code == 404
    assert _cancel(client, admin, appt).status_code == 403
    assert _cancel(client, None, appt).status_code == 401
    assert _cancel(client, patient, 99999).status_code == 404
    assert _appt_status(engine, appt) == "BOOKED"


@pytest.mark.ac("E3-S3-AC5")
@pytest.mark.parametrize(
    "state", ["CHECKED_IN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"]
)
@pytest.mark.parametrize("who", ["patient", "doctor"])
def test_non_booked_states_are_409_without_event(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment,
    state: str, who: str,
) -> None:
    appt, _ = _book_at(client, engine, doctor[0], patient, NOW + timedelta(hours=5))
    with Session(engine) as session:
        session.execute(update(Appointment).where(Appointment.appointment_id == appt)
                        .values(status=state))
        session.commit()
    response = _cancel(client, patient if who == "patient" else doctor[1], appt)
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_APPOINTMENT_STATE"
    assert len(_events(engine, appt)) == 1
    assert [c[0] for c in payment.calls] == ["charge"]
