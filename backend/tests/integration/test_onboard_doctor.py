"""E2-S2: admin onboards a doctor with an availability template (API-16)."""
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.api.deps import require_roles
from telemed.repository.models import AvailabilityTemplate, DoctorProfile, Slot, User
from telemed.service import security
from telemed.service.slot_generator import SlotGenerator
from telemed.types import domain
from telemed.types.enums import Role
from tests.conftest import FrozenClock

PASSWORD = "Passw0rd!"
INITIAL = "Initial-Pw-9137"
TEMPLATE = {"weekday": 0, "start_time": "09:00", "end_time": "12:00", "slot_length_minutes": 30}


def _body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "email": "Dr.Rao@example.test", "initial_password": INITIAL, "full_name": "Dr Rao",
        "specialty": "Cardiology", "languages": ["en", "hi"], "fee": "500.00",
        "availability_templates": [dict(TEMPLATE)],
    }
    body.update(overrides)
    return body


@pytest.fixture
def app(
    db_path: Path, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> FastAPI:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    return create_app(clock=frozen_clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _insert(engine: Engine, email: str, role: Role) -> None:
    now = datetime(2026, 10, 6, tzinfo=UTC)
    with Session(engine) as session:
        session.add(
            User(
                email=email, password_hash=security.hash_password(PASSWORD), role=role.value,
                active=1, created_at=now, updated_at=now,
            )
        )
        session.commit()


def _login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(client: TestClient, engine: Engine) -> dict[str, str]:
    _insert(engine, "admin@example.test", Role.ADMIN)
    return _login(client, "admin@example.test")


def _counts(engine: Engine) -> tuple[int, int, int, int]:
    with Session(engine) as session:
        return tuple(  # type: ignore[return-value]
            int(session.scalar(select(func.count()).select_from(model)) or 0)
            for model in (User, DoctorProfile, AvailabilityTemplate, Slot)
        )


@pytest.mark.ac("AC-E2-S2-1")
@pytest.mark.ac("AC-10")
def test_onboard_returns_201_stores_fee_and_generates_slots(
    client: TestClient, engine: Engine, admin: dict[str, str]
) -> None:
    response = client.post("/api/admin/doctors", json=_body(), headers=admin)
    assert response.status_code == 201
    body = response.json()
    assert body["doctor_id"] == body["user_id"]
    assert body["email"] == "dr.rao@example.test"
    assert (body["fee"], body["languages"], body["slots_created"]) == ("500.00", ["en", "hi"], 12)
    assert body["availability_templates"] == [{**TEMPLATE, "template_id": 1}]
    assert "password" not in response.text and INITIAL not in response.text
    with Session(engine) as session:
        user = session.get(User, body["doctor_id"])
        assert user is not None and user.role == "DOCTOR" and user.active == 1
        assert user.password_hash.startswith("$argon2") and INITIAL not in user.password_hash
        assert session.get(DoctorProfile, body["doctor_id"]).fee_minor == 50000  # type: ignore[union-attr]
        slots = list(session.scalars(select(Slot)))
    assert len(slots) == 12
    assert {s.start_time.weekday() for s in slots} == {0}
    assert all(s.status == "AVAILABLE" and s.start_time > datetime(2026, 10, 6, tzinfo=UTC)
               for s in slots)


@pytest.mark.ac("AC-E2-S2-1")
def test_onboard_normalises_fee_languages_and_defaults_name(
    client: TestClient, admin: dict[str, str]
) -> None:
    two_windows = [
        TEMPLATE,
        {"weekday": 0, "start_time": "14:00", "end_time": "15:00", "slot_length_minutes": 30},
    ]
    response = client.post(
        "/api/admin/doctors",
        json=_body(fee="500.5", languages=["EN", "hi", "en"], full_name=None,
                   availability_templates=two_windows),
        headers=admin,
    )
    body = response.json()
    assert response.status_code == 201
    assert (body["fee"], body["languages"], body["full_name"]) == ("500.50", ["en", "hi"], "dr.rao")
    assert body["slots_created"] == 16
    free = client.post("/api/admin/doctors", json=_body(email="f@example.test", fee="0.00"),
                       headers=admin)
    assert free.status_code == 201 and free.json()["fee"] == "0.00"


@pytest.mark.ac("AC-E2-S2-2")
def test_non_admin_and_anonymous_are_refused_before_validation(
    client: TestClient, engine: Engine, admin: dict[str, str]
) -> None:
    client.post("/api/auth/register", json={
        "email": "p@example.test", "password": PASSWORD, "full_name": "P", "age": 30,
        "gender": "MALE", "phone": "1"})
    client.post("/api/admin/doctors", json=_body(email="doc@example.test"), headers=admin)
    before = _counts(engine)
    assert client.post("/api/admin/doctors", json=_body()).status_code == 401
    assert client.post("/api/admin/doctors", json={}).status_code == 401
    bad = {"Authorization": "Bearer junk"}
    assert client.post("/api/admin/doctors", json=_body(), headers=bad).status_code == 401
    for email in ("p@example.test",):
        headers = _login(client, email)
        assert client.post("/api/admin/doctors", json=_body(), headers=headers).status_code == 403
        invalid = client.post("/api/admin/doctors", json={}, headers=headers)
        assert invalid.status_code == 403
    doctor_headers = _login(client, "doc@example.test", INITIAL)
    doctor = client.post("/api/admin/doctors", json=_body(), headers=doctor_headers)
    assert doctor.status_code == 403 and doctor.json()["code"] == "FORBIDDEN"
    assert _counts(engine) == before


@pytest.mark.ac("AC-E2-S2-3")
@pytest.mark.parametrize(
    ("template", "field"),
    [
        ({"start_time": "09:00", "end_time": "09:00"}, "end_time"),
        ({"start_time": "10:00", "end_time": "09:00"}, "end_time"),
        ({"slot_length_minutes": 0}, "slot_length_minutes"),
        ({"slot_length_minutes": -30}, "slot_length_minutes"),
        ({"start_time": "09:00", "end_time": "10:40"}, "slot_length_minutes"),
        ({"start_time": "9am"}, "start_time"),
        ({"weekday": 7}, "weekday"),
    ],
)
def test_invalid_template_is_422_and_persists_nothing(
    client: TestClient, engine: Engine, admin: dict[str, str], template: dict[str, Any], field: str
) -> None:
    before = _counts(engine)
    body = _body(availability_templates=[{**TEMPLATE, **template}])
    response = client.post("/api/admin/doctors", json=body, headers=admin)
    assert response.status_code == 422
    assert f"availability_templates[0].{field}" in [e["field"] for e in response.json()["errors"]]
    assert _counts(engine) == before
    assert client.post("/api/admin/doctors", json=_body(), headers=admin).status_code == 201


@pytest.mark.ac("AC-E2-S2-3")
def test_overlap_and_error_index_one_are_reported(
    client: TestClient, engine: Engine, admin: dict[str, str]
) -> None:
    before = _counts(engine)
    overlap = {**TEMPLATE, "start_time": "11:00", "end_time": "13:00"}
    invalid_second = {**TEMPLATE, "slot_length_minutes": 0, "weekday": 1}
    touching = {**TEMPLATE, "start_time": "12:00", "end_time": "13:00"}
    for rows, expected in (
        ([TEMPLATE, overlap], "availability_templates[1].start_time"),
        ([TEMPLATE, invalid_second], "availability_templates[1].slot_length_minutes"),
    ):
        response = client.post(
            "/api/admin/doctors", json=_body(availability_templates=rows), headers=admin
        )
        assert response.status_code == 422
        assert expected in [e["field"] for e in response.json()["errors"]]
    assert _counts(engine) == before
    ok = client.post("/api/admin/doctors",
                     json=_body(availability_templates=[TEMPLATE, touching]), headers=admin)
    assert ok.status_code == 201


@pytest.mark.ac("AC-E2-S2-4")
@pytest.mark.parametrize("fee", ["abc", "-1.00", "500.123", "", 500, 500.5, None])
def test_bad_fee_is_422_without_echo_and_persists_nothing(
    client: TestClient, engine: Engine, admin: dict[str, str], fee: Any
) -> None:
    before = _counts(engine)
    response = client.post("/api/admin/doctors", json=_body(fee=fee), headers=admin)
    assert response.status_code == 422
    assert "fee" in [e["field"] for e in response.json()["errors"]]
    if isinstance(fee, str) and fee:
        assert fee not in response.text
    assert _counts(engine) == before


@pytest.mark.ac("AC-E2-S2-4")
@pytest.mark.parametrize(
    "overrides",
    [{"languages": []}, {"languages": ["e"]}, {"languages": ["en1"]}, {"specialty": ""},
     {"initial_password": "short"}, {"email": "nope"}, {"availability_templates": []}],
)
def test_other_invalid_fields_are_422(
    client: TestClient, admin: dict[str, str], overrides: dict[str, Any]
) -> None:
    response = client.post("/api/admin/doctors", json=_body(**overrides), headers=admin)
    assert response.status_code == 422


@pytest.mark.ac("AC-E2-S2-5")
def test_duplicate_email_is_409_in_any_case_and_creates_nothing(
    client: TestClient, engine: Engine, admin: dict[str, str]
) -> None:
    assert client.post("/api/admin/doctors", json=_body(), headers=admin).status_code == 201
    before = _counts(engine)
    for email in ("dr.rao@example.test", "DR.RAO@example.test", "admin@example.test"):
        response = client.post("/api/admin/doctors", json=_body(email=email), headers=admin)
        assert response.status_code == 409
        assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"
    assert _counts(engine) == before


@pytest.mark.ac("AC-E2-S2-6")
def test_onboarded_doctor_can_login_and_hits_doctor_only_route(
    app: FastAPI, client: TestClient, admin: dict[str, str]
) -> None:
    router = APIRouter()
    doctor_guard = require_roles(Role.DOCTOR)

    @router.get("/t/doctor-only")
    def doctor_only(user: domain.User = Depends(doctor_guard)) -> dict[str, str]:
        return {"role": user.role.value}

    app.include_router(router)
    created = client.post("/api/admin/doctors", json=_body(), headers=admin).json()
    login = client.post(
        "/api/auth/login", json={"email": "dr.rao@example.test", "password": INITIAL}
    )
    assert login.status_code == 200
    assert (login.json()["role"], login.json()["user_id"]) == ("DOCTOR", created["doctor_id"])
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/t/doctor-only", headers=headers).json() == {"role": "DOCTOR"}
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "DOCTOR"
    wrong = client.post(
        "/api/auth/login", json={"email": "dr.rao@example.test", "password": "Wrong-pass-1"}
    )
    assert wrong.status_code == 401
    assert client.get("/t/doctor-only", headers=admin).status_code == 403


@pytest.mark.ac("AC-E2-S2-3")
def test_failure_in_slot_generation_rolls_back_atomically(
    client: TestClient, engine: Engine, admin: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: SlotGenerator, session: Session, doctor_id: int) -> int:
        raise RuntimeError("injected")

    before = _counts(engine)
    monkeypatch.setattr(SlotGenerator, "generate_for", boom)
    failing = TestClient(client.app, raise_server_exceptions=False)
    response = failing.post("/api/admin/doctors", json=_body(), headers=admin)
    assert response.status_code == 500
    assert _counts(engine) == before
    monkeypatch.undo()
    assert client.post("/api/admin/doctors", json=_body(), headers=admin).status_code == 201


@pytest.mark.ac("AC-E2-S2-1")
def test_onboarding_logs_user_id_and_never_the_password(
    client: TestClient, admin: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        created = client.post("/api/admin/doctors", json=_body(), headers=admin).json()
    records = [r for r in caplog.records if r.name == "telemed.doctors"]
    assert any(getattr(r, "user_id", None) == created["doctor_id"] for r in records)
    assert INITIAL not in " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
