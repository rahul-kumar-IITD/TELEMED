"""E4-S2: admin user management and patient profile edits (API-17..20)."""
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.repository.models import Appointment, PatientProfileVersion, Slot, User
from telemed.service import security
from telemed.types.enums import Role
from tests.conftest import FrozenClock

PASSWORD = "Passw0rd!"
NOW = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
TEMPLATES = [
    {"weekday": d, "start_time": "09:00", "end_time": "10:00", "slot_length_minutes": 30}
    for d in range(7)
]
Headers = dict[str, str]


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


def _login(client: TestClient, email: str) -> Headers:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _register(client: TestClient, email: str) -> tuple[int, Headers]:
    response = client.post("/api/auth/register", json={
        "email": email, "password": PASSWORD, "full_name": "Pat Ient", "age": 30,
        "gender": "MALE", "phone": "1"})
    return int(response.json()["user_id"]), _login(client, email)


@pytest.fixture
def admin(client: TestClient, engine: Engine) -> tuple[int, Headers]:
    with Session(engine) as session:
        user = User(email="admin@example.test", password_hash=security.hash_password(PASSWORD),
                    role=Role.ADMIN.value, active=1, created_at=NOW, updated_at=NOW)
        session.add(user)
        session.commit()
        user_id = int(user.user_id)
    return user_id, _login(client, "admin@example.test")


def _onboard(client: TestClient, admin: Headers, email: str) -> int:
    response = client.post("/api/admin/doctors", headers=admin, json={
        "email": email, "initial_password": PASSWORD, "full_name": "Dr Rao",
        "specialty": "Cardiology", "languages": ["en"], "fee": "500",
        "availability_templates": TEMPLATES})
    assert response.status_code == 201
    return int(response.json()["doctor_id"])


def _book(client: TestClient, engine: Engine, doctor_id: int, patient: Headers) -> int:
    with Session(engine) as session:
        slot_id = int(session.scalars(
            select(Slot.slot_id).where(Slot.doctor_id == doctor_id).order_by(Slot.start_time)
        ).first() or 0)
    response = client.post("/api/appointments", headers=patient, json={"slot_id": slot_id})
    assert response.status_code == 201
    return int(response.json()["appointment_id"])


def _set_status(engine: Engine, appointment_id: int, status: str) -> None:
    with Session(engine) as session:
        session.execute(update(Appointment).where(Appointment.appointment_id == appointment_id)
                        .values(status=status))
        session.commit()


@pytest.mark.ac("E4-S2-AC1")
def test_list_users_filter_and_validation(
    client: TestClient, admin: tuple[int, Headers]
) -> None:
    headers = admin[1]
    _onboard(client, headers, "d@example.test")
    _, patient = _register(client, "p@example.test")
    body = client.get("/api/admin/users", headers=headers).json()
    assert body["total"] == 3
    assert [u["user_id"] for u in body["items"]] == sorted(u["user_id"] for u in body["items"])
    assert {u["role"] for u in body["items"]} == {"ADMIN", "DOCTOR", "PATIENT"}
    assert all(isinstance(u["active"], bool) for u in body["items"])
    doctors = client.get("/api/admin/users?role=DOCTOR", headers=headers).json()
    assert [u["role"] for u in doctors["items"]] == ["DOCTOR"]
    assert doctors["items"][0]["full_name"] == "Dr Rao"
    client.put(f"/api/admin/users/{doctors['items'][0]['user_id']}/deactivate", headers=headers)
    inactive = client.get("/api/admin/users?active=false", headers=headers).json()
    assert [u["role"] for u in inactive["items"]] == ["DOCTOR"]
    assert client.get("/api/admin/users?role=BAD", headers=headers).status_code == 422
    assert client.get("/api/admin/users", headers=patient).status_code == 403
    assert client.get("/api/admin/users").status_code == 401


@pytest.mark.ac("E4-S2-AC2")
def test_deactivate_patient_blocks_login_and_token_keeps_appointments(
    client: TestClient, engine: Engine, admin: tuple[int, Headers]
) -> None:
    headers = admin[1]
    doctor_id = _onboard(client, headers, "d@example.test")
    patient_id, patient = _register(client, "p@example.test")
    appt = _book(client, engine, doctor_id, patient)
    response = client.put(f"/api/admin/users/{patient_id}/deactivate", headers=headers)
    assert response.status_code == 200
    assert response.json()["active"] is False
    login = client.post("/api/auth/login", json={"email": "p@example.test", "password": PASSWORD})
    assert login.status_code == 401
    assert client.get("/api/auth/me", headers=patient).status_code == 401
    with Session(engine) as session:
        assert session.get(Appointment, appt) is not None
    listed = client.get("/api/admin/users?role=PATIENT", headers=headers).json()
    assert listed["items"][0]["active"] is False
    again = client.put(f"/api/admin/users/{patient_id}/deactivate", headers=headers)
    assert again.status_code == 200


@pytest.mark.ac("E4-S2-AC3")
@pytest.mark.parametrize("state", ["BOOKED", "CHECKED_IN", "IN_PROGRESS"])
def test_doctor_with_open_appointment_cannot_be_deactivated(
    client: TestClient, engine: Engine, admin: tuple[int, Headers], state: str
) -> None:
    headers = admin[1]
    doctor_id = _onboard(client, headers, "d@example.test")
    _, patient = _register(client, "p@example.test")
    _set_status(engine, _book(client, engine, doctor_id, patient), state)
    response = client.put(f"/api/admin/users/{doctor_id}/deactivate", headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "ACTIVE_APPOINTMENTS_EXIST"
    assert client.get(f"/api/doctors/{doctor_id}", headers=patient).status_code == 200


@pytest.mark.ac("E4-S2-AC3")
def test_doctor_with_terminal_appointments_deactivates_and_leaves_search(
    client: TestClient, engine: Engine, admin: tuple[int, Headers]
) -> None:
    headers = admin[1]
    doctor_id = _onboard(client, headers, "d@example.test")
    _, patient = _register(client, "p@example.test")
    _set_status(engine, _book(client, engine, doctor_id, patient), "COMPLETED")
    response = client.put(f"/api/admin/users/{doctor_id}/deactivate", headers=headers)
    assert response.status_code == 200
    assert client.get("/api/doctors", headers=patient).json()["items"] == []
    reactivated = client.put(f"/api/admin/users/{doctor_id}/reactivate", headers=headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["active"] is True
    assert len(client.get("/api/doctors", headers=patient).json()["items"]) == 1


@pytest.mark.ac("E4-S2-AC4")
def test_admin_cannot_deactivate_self(client: TestClient, admin: tuple[int, Headers]) -> None:
    admin_id, headers = admin
    response = client.put(f"/api/admin/users/{admin_id}/deactivate", headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "CANNOT_DEACTIVATE_SELF"
    assert client.get("/api/auth/me", headers=headers).status_code == 200


@pytest.mark.ac("E4-S2-AC5")
def test_reactivate_patient_can_login_and_unknown_is_404(
    client: TestClient, admin: tuple[int, Headers]
) -> None:
    headers = admin[1]
    patient_id, _ = _register(client, "p@example.test")
    client.put(f"/api/admin/users/{patient_id}/deactivate", headers=headers)
    response = client.put(f"/api/admin/users/{patient_id}/reactivate", headers=headers)
    assert response.status_code == 200
    assert response.json()["active"] is True
    login = client.post("/api/auth/login", json={"email": "p@example.test", "password": PASSWORD})
    assert login.status_code == 200
    assert client.put("/api/admin/users/9999/reactivate", headers=headers).status_code == 404
    assert client.put("/api/admin/users/9999/deactivate", headers=headers).status_code == 404


@pytest.mark.ac("E4-S2-AC6")
def test_admin_profile_edit_appends_version(
    client: TestClient, engine: Engine, admin: tuple[int, Headers]
) -> None:
    admin_id, headers = admin
    patient_id, patient = _register(client, "p@example.test")
    response = client.put(
        f"/api/admin/patients/{patient_id}/profile", headers=headers,
        json={"full_name": "New Name", "age": 41, "gender": "FEMALE", "phone": "999"},
    )
    assert response.status_code == 200
    assert response.json()["version_number"] == 2
    assert response.json()["full_name"] == "New Name"
    with Session(engine) as session:
        rows = list(session.scalars(
            select(PatientProfileVersion).order_by(PatientProfileVersion.version_number)))
    assert [r.version_number for r in rows] == [1, 2]
    assert rows[0].full_name == "Pat Ient"
    assert rows[1].changed_by_user_id == admin_id
    assert client.put(f"/api/admin/patients/{admin_id}/profile", headers=headers,
                      json={"age": 5}).status_code == 404
    assert client.put(f"/api/admin/patients/{patient_id}/profile", headers=patient,
                      json={"age": 5}).status_code == 403
    assert client.put(f"/api/admin/patients/{patient_id}/profile", headers=headers,
                      json={"age": 0}).status_code == 422
