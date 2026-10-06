"""E1-S5: versioned patient profile (API-06/07/08) and the owner-or-admin update rule."""
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.repository.models import PatientProfileVersion, User
from telemed.service import security
from telemed.service.container import Container
from telemed.service.profile_service import ProfileService
from telemed.types import domain
from telemed.types.domain import ProfileChanges
from telemed.types.enums import Gender, Role
from telemed.types.errors import ForbiddenException, NotFoundException
from telemed.types.ids import UserId
from tests.conftest import FrozenClock
from tests.factories import add_doctor

PASSWORD = "Passw0rd!"


@pytest.fixture
def client(
    db_path: Path, engine: Engine, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    with TestClient(create_app(clock=frozen_clock)) as test_client:
        yield test_client


def _register(client: TestClient, email: str, **overrides: Any) -> tuple[int, dict[str, str]]:
    body = {"email": email, "password": PASSWORD, "full_name": "Pat One", "age": 34,
            "gender": "FEMALE", "phone": "+911234567890"}
    body.update(overrides)
    user_id = client.post("/api/auth/register", json=body).json()["user_id"]
    return int(user_id), _login(client, email)


def _login(client: TestClient, email: str) -> dict[str, str]:
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _doctor_headers(frozen_clock: FrozenClock, doctor_id: int) -> dict[str, str]:
    """The factory doctor has a placeholder hash, so mint a token for the real user row."""
    token = security.issue_token(
        UserId(doctor_id), "DOCTOR", "integration-secret-at-least-32-bytes-0123",
        frozen_clock.now(), 30,
    )
    return {"Authorization": f"Bearer {token.access_token}"}


def _insert_user(engine: Engine, email: str, role: Role) -> int:
    now = datetime(2026, 10, 6, tzinfo=UTC)
    with Session(engine) as session:
        row = User(
            email=email, password_hash=security.hash_password(PASSWORD), role=role.value,
            active=1, created_at=now, updated_at=now,
        )
        session.add(row)
        session.commit()
        return int(row.user_id)


def _versions(engine: Engine, patient_id: int | None = None) -> list[tuple[Any, ...]]:
    stmt = select(PatientProfileVersion).order_by(PatientProfileVersion.version_id)
    if patient_id is not None:
        stmt = stmt.where(PatientProfileVersion.patient_id == patient_id)
    with Session(engine) as session:
        return [
            (r.version_id, r.patient_id, r.version_number, r.full_name, r.age, r.gender,
             r.phone, r.changed_by_user_id, r.created_at)
            for r in session.scalars(stmt)
        ]


def _count(engine: Engine) -> int:
    with Session(engine) as session:
        return int(session.scalar(select(func.count()).select_from(PatientProfileVersion)) or 0)


@pytest.mark.ac("AC-E1-S5-1")
def test_get_own_profile_returns_latest_version(client: TestClient) -> None:
    user_id, headers = _register(client, "p1@example.test")
    response = client.get("/api/patients/me/profile", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "patient_id": user_id, "version_number": 1, "full_name": "Pat One", "age": 34,
        "gender": "FEMALE", "phone": "+911234567890", "updated_at": "2026-10-06T00:00:00Z",
    }


@pytest.mark.ac("AC-E1-S5-1")
def test_profile_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/patients/me/profile").status_code == 401
    assert client.put("/api/patients/me/profile", json={"age": 40}).status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert client.get("/api/patients/me/profile", headers=bad).status_code == 401


@pytest.mark.ac("AC-E1-S5-2")
def test_update_inserts_new_version_and_keeps_earlier_rows_identical(
    client: TestClient, engine: Engine, frozen_clock: FrozenClock
) -> None:
    user_id, headers = _register(client, "p1@example.test")
    before = _versions(engine, user_id)
    response = client.put("/api/patients/me/profile", json={"phone": "+91999"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert (body["version_number"], body["phone"], body["full_name"], body["age"]) == (
        2, "+91999", "Pat One", 34,
    )
    after = _versions(engine, user_id)
    assert after[:1] == before
    assert len(after) == 2
    assert after[1][7] == user_id  # changed_by_user_id


@pytest.mark.ac("AC-E1-S5-3")
def test_two_updates_then_get_returns_second_with_history_kept(
    client: TestClient, engine: Engine
) -> None:
    user_id, headers = _register(client, "p1@example.test")
    client.put("/api/patients/me/profile", json={"full_name": "A", "age": 40}, headers=headers)
    client.put("/api/patients/me/profile", json={"full_name": "B", "phone": "222"}, headers=headers)
    current = client.get("/api/patients/me/profile", headers=headers).json()
    assert (current["full_name"], current["phone"], current["age"]) == ("B", "222", 40)
    assert current["version_number"] == 3
    rows = _versions(engine, user_id)
    assert [r[3] for r in rows] == ["Pat One", "A", "B"]


@pytest.mark.ac("AC-E1-S5-4")
def test_doctor_and_admin_get_403_on_me_routes_without_new_rows(
    client: TestClient, engine: Engine, frozen_clock: FrozenClock
) -> None:
    _register(client, "p1@example.test")
    doctor_id = add_doctor(engine, "d@example.test", [])
    _insert_user(engine, "a@example.test", Role.ADMIN)
    rows = _count(engine)
    for headers in (_doctor_headers(frozen_clock, doctor_id), _login(client, "a@example.test")):
        assert client.get("/api/patients/me/profile", headers=headers).status_code == 403
        invalid = client.put("/api/patients/me/profile", json={}, headers=headers)
        assert invalid.status_code == 403  # access order: 403 before 422
        assert invalid.json()["code"] == "FORBIDDEN"
    assert _count(engine) == rows


@pytest.mark.ac("AC-E1-S5-4")
def test_foreign_missing_and_non_patient_ids_are_identical_404(
    client: TestClient, engine: Engine, frozen_clock: FrozenClock
) -> None:
    a_id, a_headers = _register(client, "a@example.test")
    _, b_headers = _register(client, "b@example.test")
    doctor_id = add_doctor(engine, "d@example.test", [])
    admin_id = _insert_user(engine, "adm@example.test", Role.ADMIN)
    responses = [
        client.get(f"/api/patients/{pid}/profile", headers=b_headers)
        for pid in (a_id, 9999, doctor_id, admin_id)
    ]
    assert all(r.status_code == 404 for r in responses)
    assert len({r.content for r in responses}) == 1
    assert client.get(f"/api/patients/{a_id}/profile", headers=a_headers).status_code == 200
    doctor_headers = _doctor_headers(frozen_clock, doctor_id)
    assert client.get(f"/api/patients/{a_id}/profile", headers=doctor_headers).status_code == 403
    admin_headers = _login(client, "adm@example.test")
    assert client.get(f"/api/patients/{a_id}/profile", headers=admin_headers).status_code == 200
    assert client.get("/api/patients/9999/profile", headers=admin_headers).status_code == 404


@pytest.mark.ac("AC-E1-S5-5")
def test_update_log_contains_user_id_but_no_phi(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    user_id, headers = _register(client, "p1@example.test")
    with caplog.at_level(logging.DEBUG):
        client.put(
            "/api/patients/me/profile",
            json={"full_name": "Zq7UniqueName", "phone": "+91-555-UNIQ", "age": 77},
            headers=headers,
        )
    records = [r for r in caplog.records if r.name == "telemed.profile"]
    assert any(getattr(r, "user_id", None) == user_id for r in records)
    text = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert "Zq7UniqueName" not in text and "+91-555-UNIQ" not in text


@pytest.mark.ac("AC-E1-S5-6")
@pytest.mark.parametrize(
    ("field", "value"), [("full_name", "New"), ("age", 1), ("age", 130), ("gender", "MALE"),
                         ("phone", "555")],
)
def test_each_single_field_can_change_alone(
    client: TestClient, field: str, value: Any
) -> None:
    _, headers = _register(client, "p1@example.test")
    response = client.put("/api/patients/me/profile", json={field: value}, headers=headers)
    assert response.status_code == 200
    assert response.json()[field] == value


@pytest.mark.ac("AC-E1-S5-6")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "body"), ({"age": 0}, "age"), ({"age": 131}, "age"), ({"age": -1}, "age"),
        ({"age": 30.5}, "age"), ({"age": "30"}, "age"), ({"gender": "X"}, "gender"),
        ({"full_name": ""}, "full_name"), ({"full_name": "   "}, "full_name"),
        ({"full_name": "x" * 201}, "full_name"), ({"phone": ""}, "phone"),
        ({"phone": "1" * 33}, "phone"), ({"age": None}, "age"), ({"gender": None}, "gender"),
        ({"full_name": None}, "full_name"), ({"phone": None}, "phone"),
    ],
)
def test_invalid_updates_are_422_with_field_and_add_no_row(
    client: TestClient, engine: Engine, body: dict[str, Any], field: str
) -> None:
    _, headers = _register(client, "p1@example.test")
    rows = _count(engine)
    response = client.put("/api/patients/me/profile", json=body, headers=headers)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert field in [e["field"] for e in response.json()["errors"]]
    assert _count(engine) == rows


@pytest.mark.ac("AC-E1-S5-6")
def test_unknown_field_is_ignored_and_role_unchanged(
    client: TestClient, engine: Engine
) -> None:
    user_id, headers = _register(client, "p1@example.test")
    response = client.put(
        "/api/patients/me/profile", json={"age": 41, "role": "ADMIN"}, headers=headers
    )
    assert response.status_code == 200
    with Session(engine) as session:
        assert session.get(User, user_id).role == "PATIENT"  # type: ignore[union-attr]


@pytest.fixture
def service(client: TestClient) -> ProfileService:
    container: Container = client.app.state.container  # type: ignore[attr-defined]
    return container.profiles


def _actor(user_id: int, role: Role) -> domain.User:
    now = datetime(2026, 10, 6, tzinfo=UTC)
    return domain.User(UserId(user_id), "x@example.test", role, True, now, now)


@pytest.mark.ac("AC-E1-S5-6")
def test_service_accepts_owner_and_admin_with_changed_by_recorded(
    client: TestClient, engine: Engine, service: ProfileService
) -> None:
    patient_id, _ = _register(client, "p1@example.test")
    admin_id = _insert_user(engine, "adm@example.test", Role.ADMIN)
    changes = ProfileChanges(gender=Gender.OTHER)
    owner = service.update(_actor(patient_id, Role.PATIENT), UserId(patient_id), changes)
    admin = service.update(_actor(admin_id, Role.ADMIN), UserId(patient_id), changes)
    assert (owner.version_number, admin.version_number) == (2, 3)
    assert [r[7] for r in _versions(engine, patient_id)] == [patient_id, patient_id, admin_id]


@pytest.mark.ac("AC-E1-S5-6")
def test_service_refuses_doctor_and_other_patient_with_forbidden(
    client: TestClient, engine: Engine, service: ProfileService
) -> None:
    patient_id, _ = _register(client, "p1@example.test")
    other_id, _ = _register(client, "p2@example.test")
    rows = _count(engine)
    changes = ProfileChanges(age=50)
    with pytest.raises(ForbiddenException):
        service.update(_actor(77, Role.DOCTOR), UserId(patient_id), changes)
    with pytest.raises(ForbiddenException):
        service.update(_actor(other_id, Role.PATIENT), UserId(patient_id), changes)
    assert _count(engine) == rows


@pytest.mark.ac("AC-E1-S5-6")
def test_service_update_of_unknown_patient_is_not_found_for_admin(
    client: TestClient, service: ProfileService
) -> None:
    with pytest.raises(NotFoundException):
        service.update(_actor(1, Role.ADMIN), UserId(4242), ProfileChanges(age=50))
