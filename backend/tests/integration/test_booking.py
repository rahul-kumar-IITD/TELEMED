"""E3-S2: atomic patient booking (API-21)."""
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from telemed.api import deps
from telemed.api.app import create_app
from telemed.repository.models import Appointment, AppointmentEvent, Slot, User
from telemed.service import security
from telemed.types.enums import Role
from tests.conftest import FrozenClock, SpyPayment

PASSWORD = "Passw0rd!"
INITIAL = "Initial-Pw-9137"
NOW = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
TEMPLATES = [
    {"weekday": d, "start_time": "09:00", "end_time": "11:00", "slot_length_minutes": 30}
    for d in range(7)
]
Headers = dict[str, str]


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


def _login(client: TestClient, email: str, password: str = PASSWORD) -> Headers:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
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


@pytest.fixture
def doctor(client: TestClient, admin: Headers) -> dict[str, object]:
    response = client.post("/api/admin/doctors", headers=admin, json={
        "email": "d@example.test", "initial_password": INITIAL, "full_name": "Dr Rao",
        "specialty": "Cardiology", "languages": ["en"], "fee": "500",
        "availability_templates": TEMPLATES})
    assert response.status_code == 201
    body: dict[str, object] = response.json()
    return body


@pytest.fixture
def patient(client: TestClient) -> Headers:
    return _register(client, "p@example.test")


def _slot_ids(engine: Engine, doctor_id: object) -> list[int]:
    stmt = select(Slot.slot_id).where(Slot.doctor_id == doctor_id).order_by(Slot.start_time)
    with Session(engine) as session:
        return [int(i) for i in session.scalars(stmt)]


def _count(engine: Engine, model: type) -> int:
    with Session(engine) as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _status(engine: Engine, slot_id: int) -> str:
    with Session(engine) as session:
        row = session.get(Slot, slot_id)
        assert row is not None
        return row.status


def _set_slot(engine: Engine, slot_id: int, **values: object) -> None:
    with Session(engine) as session:
        session.execute(update(Slot).where(Slot.slot_id == slot_id).values(**values))
        session.commit()


def _book(client: TestClient, headers: Headers, slot_id: object) -> tuple[int, dict[str, object]]:
    response = client.post("/api/appointments", headers=headers, json={"slot_id": slot_id})
    return response.status_code, response.json()


def test_book_available_slot_creates_appointment_and_event(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers,
    payment: SpyPayment,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    status, body = _book(client, patient, slot_id)
    assert status == 201
    assert body["status"] == "BOOKED"
    assert body["slot_id"] == slot_id
    assert body["fee"] == "500.00"
    assert body["doctor"] == {
        "doctor_id": doctor["doctor_id"], "full_name": "Dr Rao", "specialty": "Cardiology"}
    assert body["patient"]["full_name"] == "Pat Ient"  # type: ignore[index]
    assert body["allowed_actions"] == ["CANCEL", "RESCHEDULE"]
    assert body["join_url"]
    assert _status(engine, slot_id) == "BOOKED"
    assert _count(engine, Appointment) == 1
    with Session(engine) as session:
        events = list(session.scalars(select(AppointmentEvent)))
        appointment = session.scalars(select(Appointment)).one()
    assert [e.event_type for e in events] == ["BOOKED"]
    assert events[0].appointment_id == body["appointment_id"]
    assert appointment.fee_minor == 50000
    assert payment.calls == [("charge", body["appointment_id"], Decimal("500.00"))]
    listing = client.get(f"/api/doctors/{doctor['doctor_id']}/slots", headers=patient).json()
    assert slot_id not in [item["slot_id"] for item in listing["items"]]


def test_payment_charged_once_on_success_and_never_on_conflict(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers,
    payment: SpyPayment,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    assert _book(client, patient, slot_id)[0] == 201
    assert len(payment.calls) == 1
    other = _register(client, "q@example.test")
    assert _book(client, other, slot_id)[0] == 409
    assert len(payment.calls) == 1


def test_twenty_concurrent_bookings_one_winner(
    client: TestClient, engine: Engine, doctor: dict[str, object], payment: SpyPayment,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    tokens = [_register(client, f"c{i}@example.test") for i in range(20)]
    barrier = Barrier(20)

    def attempt(headers: Headers) -> int:
        barrier.wait()
        return client.post(
            "/api/appointments", headers=headers, json={"slot_id": slot_id}
        ).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(attempt, tokens))
    assert sorted(codes) == [201] + [409] * 19
    assert _count(engine, Appointment) == 1
    assert _count(engine, AppointmentEvent) == 1
    assert _status(engine, slot_id) == "BOOKED"
    assert len(payment.calls) == 1


@pytest.mark.parametrize("state", ["BOOKED", "BLOCKED"])
def test_non_available_slot_is_409(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers, state: str,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    _set_slot(engine, slot_id, status=state)
    status, body = _book(client, patient, slot_id)
    assert (status, body["code"]) == (409, "SLOT_UNAVAILABLE")
    assert _count(engine, Appointment) == 0
    assert _count(engine, AppointmentEvent) == 0


def test_past_and_beyond_window_slots_are_409(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers,
    payment: SpyPayment,
) -> None:
    first, second, third = _slot_ids(engine, doctor["doctor_id"])[:3]
    _set_slot(engine, first, start_time=NOW - timedelta(hours=1),
              end_time=NOW - timedelta(minutes=30))
    _set_slot(engine, second, start_time=NOW + timedelta(days=15),
              end_time=NOW + timedelta(days=15, minutes=30))
    _set_slot(engine, third, start_time=NOW + timedelta(days=14),
              end_time=NOW + timedelta(days=14, minutes=30))
    for slot_id in (first, second, third):
        assert _book(client, patient, slot_id)[0] == 409
        assert _status(engine, slot_id) == "AVAILABLE"
    assert _count(engine, Appointment) == 0
    assert payment.calls == []


def test_slot_just_inside_window_books_and_late_slot_has_no_actions(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers,
) -> None:
    first, second = _slot_ids(engine, doctor["doctor_id"])[:2]
    _set_slot(engine, first, start_time=NOW + timedelta(days=13, hours=23),
              end_time=NOW + timedelta(days=13, hours=23, minutes=30))
    assert _book(client, patient, first)[0] == 201
    _set_slot(engine, second, start_time=NOW + timedelta(minutes=30),
              end_time=NOW + timedelta(minutes=60))
    status, body = _book(client, patient, second)
    assert status == 201
    assert body["allowed_actions"] == []


def test_deactivated_doctor_slot_is_409(
    client: TestClient, engine: Engine, doctor: dict[str, object], patient: Headers,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    with Session(engine) as session:
        session.execute(update(User).where(User.user_id == doctor["doctor_id"]).values(active=0))
        session.commit()
    status, body = _book(client, patient, slot_id)
    assert (status, body["code"]) == (409, "SLOT_UNAVAILABLE")
    assert _status(engine, slot_id) == "AVAILABLE"
    assert _count(engine, Appointment) == 0


def test_doctor_and_admin_are_forbidden_and_anonymous_is_401(
    client: TestClient, engine: Engine, doctor: dict[str, object], admin: Headers,
) -> None:
    slot_id = _slot_ids(engine, doctor["doctor_id"])[0]
    doctor_headers = _login(client, "d@example.test", INITIAL)
    assert _book(client, doctor_headers, slot_id)[0] == 403
    assert _book(client, admin, slot_id)[0] == 403
    assert _book(client, doctor_headers, 999999)[0] == 403
    assert client.post("/api/appointments", json={"slot_id": slot_id}).status_code == 401
    assert client.post("/api/appointments", json={}).status_code == 401
    assert _status(engine, slot_id) == "AVAILABLE"
    assert _count(engine, Appointment) == 0


def test_unknown_slot_is_404_and_bad_body_is_422(
    client: TestClient, patient: Headers,
) -> None:
    status, body = _book(client, patient, 999999)
    assert (status, body["code"]) == (404, "NOT_FOUND")
    for bad in ("abc", None, 1.5, True):
        status, body = _book(client, patient, bad)
        assert (status, body["code"]) == (422, "VALIDATION_ERROR")
    response = client.post("/api/appointments", headers=patient, json={})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "slot_id"
