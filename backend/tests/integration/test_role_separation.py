"""E1-S4: server-side authentication and role separation (401 -> 403 -> 404)."""
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.api.deps import require_roles
from telemed.repository.models import DoctorProfile, User
from telemed.service import access, security
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import UserId
from tests.conftest import FrozenClock

SECRET = "integration-secret-at-least-32-bytes-0123"
PASSWORD = "Passw0rd!"
UNAUTH = {"code": "UNAUTHENTICATED", "message": "Authentication required."}


class Env:
    def __init__(self, client: TestClient, engine: Engine, clock: FrozenClock) -> None:
        self.client = client
        self.engine = engine
        self.clock = clock

    def register(self, email: str) -> int:
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": PASSWORD, "full_name": f"Name {email}",
                  "age": 30, "gender": "FEMALE", "phone": "+911234567890"},
        )
        assert response.status_code == 201
        return int(response.json()["user_id"])

    def insert_staff(self, email: str, role: Role) -> int:
        now = self.clock.now()
        with Session(self.engine) as session:
            row = User(
                email=email, password_hash=security.hash_password(PASSWORD), role=role.value,
                active=1, created_at=now, updated_at=now,
            )
            session.add(row)
            session.commit()
            return int(row.user_id)

    def token(self, user_id: int, role: str) -> str:
        return security.issue_token(
            UserId(user_id), role, SECRET, self.clock.now(), 30
        ).access_token

    def login(self, email: str) -> str:
        response = self.client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        return str(response.json()["access_token"])

    def set_column(self, user_id: int, column: str, value: Any) -> None:
        with Session(self.engine) as session:
            session.execute(
                text(f"UPDATE users SET {column} = :v WHERE user_id = :i"),  # noqa: S608
                {"v": value, "i": user_id},
            )
            session.commit()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


ADMIN_ONLY = require_roles(Role.ADMIN)
DOCTOR_ONLY = require_roles(Role.DOCTOR)
PATIENT_ONLY = require_roles(Role.PATIENT)
PATIENT_OR_ADMIN = require_roles(Role.PATIENT, Role.ADMIN)
DOCTOR_OR_ADMIN = require_roles(Role.DOCTOR, Role.ADMIN)
_OBJECTS: dict[int, int] = {}  # test object id -> owner user id


def _test_router() -> APIRouter:
    router = APIRouter(prefix="/t")

    @router.get("/admin")
    def admin_only(user: domain.User = Depends(ADMIN_ONLY)) -> dict[str, int]:
        return {"user_id": user.user_id}

    @router.get("/doctor")
    def doctor_only(user: domain.User = Depends(DOCTOR_ONLY)) -> dict[str, int]:
        return {"user_id": user.user_id}

    @router.get("/patient")
    def patient_only(user: domain.User = Depends(PATIENT_ONLY)) -> dict[str, int]:
        return {"user_id": user.user_id}

    @router.get("/patient-object/{object_id}")
    def patient_object(
        object_id: int,
        user: domain.User = Depends(PATIENT_OR_ADMIN),
    ) -> dict[str, int]:
        owner = _OBJECTS.get(object_id)
        access.ensure_can_read(user, None if owner is None else [owner])
        return {"object_id": object_id}

    @router.get("/doctor-object/{object_id}")
    def doctor_object(
        object_id: int,
        user: domain.User = Depends(DOCTOR_OR_ADMIN),
    ) -> dict[str, int]:
        owner = _OBJECTS.get(object_id)
        access.ensure_can_read(user, None if owner is None else [owner])
        return {"object_id": object_id}

    return router


@pytest.fixture
def env(
    db_path: Path, engine: Engine, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Env]:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", SECRET)
    app: FastAPI = create_app(clock=frozen_clock)
    app.include_router(_test_router())
    _OBJECTS.clear()
    with TestClient(app) as client:
        yield Env(client, engine, frozen_clock)


@pytest.fixture
def people(env: Env) -> dict[str, int]:
    ids = {
        "p1": env.register("p1@example.test"),
        "p2": env.register("p2@example.test"),
        "doc": env.insert_staff("doc@example.test", Role.DOCTOR),
        "admin": env.insert_staff("admin@example.test", Role.ADMIN),
    }
    _OBJECTS[10] = ids["p1"]  # patient-scoped object owned by p1
    _OBJECTS[20] = ids["doc"]  # doctor-scoped object owned by doc
    return ids


ROUTES = ["/t/admin", "/t/doctor", "/t/patient", "/t/patient-object/10", "/t/doctor-object/20"]


@pytest.mark.ac("AC-E1-S4-1")
@pytest.mark.parametrize("path", [*ROUTES, "/api/auth/me"])
def test_no_token_is_unauthenticated_on_every_route(env: Env, path: str) -> None:
    response = env.client.get(path)
    assert response.status_code == 401
    assert response.json() == UNAUTH


@pytest.mark.ac("AC-E1-S4-1")
@pytest.mark.parametrize(
    "header",
    ["Bearer garbage", "Bearer a.b.c", "Basic xxx", "Bearer ", "Bearer", "garbage", ""],
)
def test_malformed_authorization_is_unauthenticated(env: Env, header: str) -> None:
    for path in ("/api/auth/me", "/t/admin", "/t/patient-object/99"):
        response = env.client.get(path, headers={"Authorization": header})
        assert response.status_code == 401
        assert response.json() == UNAUTH


@pytest.mark.ac("AC-E1-S4-1")
def test_expired_token_is_unauthenticated(env: Env, people: dict[str, int]) -> None:
    token = env.token(people["admin"], "ADMIN")
    env.clock.advance(timedelta(minutes=31))
    for path in ("/api/auth/me", "/t/admin"):
        response = env.client.get(path, headers=_headers(token))
        assert response.status_code == 401
        assert response.json() == UNAUTH


@pytest.mark.ac("AC-E1-S4-1")
def test_wrong_signature_and_alg_none_are_unauthenticated(
    env: Env, people: dict[str, int]
) -> None:
    now = int(env.clock.now().timestamp())
    claims = {"sub": str(people["admin"]), "role": "ADMIN", "iat": now, "exp": now + 600,
              "jti": "x"}
    bad_sig = jwt.encode(claims, "another-secret-that-is-32-bytes-long-xx", algorithm="HS256")
    no_alg = jwt.encode(claims, "", algorithm="none")
    for token in (bad_sig, no_alg):
        response = env.client.get("/t/admin", headers=_headers(token))
        assert response.status_code == 401
        assert response.json() == UNAUTH


@pytest.mark.ac("AC-E1-S4-1")
def test_unauthenticated_beats_forbidden_and_not_found(env: Env) -> None:
    for path in ("/t/admin", "/t/patient-object/10", "/t/patient-object/9999"):
        assert env.client.get(path).status_code == 401


@pytest.mark.ac("AC-E1-S4-1")
def test_me_returns_user_shape_without_secrets(env: Env, people: dict[str, int]) -> None:
    response = env.client.get("/api/auth/me", headers=_headers(env.login("p1@example.test")))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user_id", "email", "role", "active", "full_name", "created_at"}
    assert body["user_id"] == people["p1"]
    assert body["role"] == "PATIENT" and body["active"] is True
    assert body["full_name"] == "Name p1@example.test"
    assert body["created_at"].endswith("Z")
    assert "password" not in response.text


@pytest.mark.ac("AC-E1-S4-1")
def test_me_full_name_null_for_admin(env: Env, people: dict[str, int]) -> None:
    token = env.login("admin@example.test")
    body = env.client.get("/api/auth/me", headers=_headers(token)).json()
    assert body["role"] == "ADMIN" and body["full_name"] is None


@pytest.mark.ac("AC-E1-S4-1")
def test_me_full_name_for_doctor_from_profile(env: Env, people: dict[str, int]) -> None:
    now = env.clock.now()
    with Session(env.engine) as session:
        session.add(
            DoctorProfile(
                doctor_id=people["doc"], full_name="Dr Who", specialty="GP",
                languages='["en"]', fee_minor=1000, created_at=now, updated_at=now,
            )
        )
        session.commit()
    body = env.client.get("/api/auth/me", headers=_headers(env.login("doc@example.test"))).json()
    assert body["role"] == "DOCTOR" and body["full_name"] == "Dr Who"


@pytest.mark.ac("AC-E1-S4-2")
def test_forged_admin_claim_is_forbidden_on_admin_route(
    env: Env, people: dict[str, int]
) -> None:
    token = env.token(people["p1"], "ADMIN")  # validly signed, claims ADMIN
    response = env.client.get("/t/admin", headers=_headers(token))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


@pytest.mark.ac("AC-E1-S4-2")
def test_role_from_db_is_used_and_reread_each_request(env: Env, people: dict[str, int]) -> None:
    token = env.token(people["p1"], "ADMIN")
    assert env.client.get("/api/auth/me", headers=_headers(token)).json()["role"] == "PATIENT"
    env.set_column(people["p1"], "role", "DOCTOR")
    assert env.client.get("/api/auth/me", headers=_headers(token)).json()["role"] == "DOCTOR"
    assert env.client.get("/t/doctor", headers=_headers(token)).status_code == 200


@pytest.mark.ac("AC-E1-S4-3")
@pytest.mark.nfr("NFR-04")
def test_wrong_role_is_forbidden(env: Env, people: dict[str, int]) -> None:
    patient = _headers(env.token(people["p1"], "PATIENT"))
    doctor = _headers(env.token(people["doc"], "DOCTOR"))
    cases = [
        (patient, "/t/doctor"), (patient, "/t/admin"),
        (doctor, "/t/patient"), (doctor, "/t/admin"),
    ]
    for headers, path in cases:
        response = env.client.get(path, headers=headers)
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
    assert env.client.get("/t/patient", headers=patient).status_code == 200


@pytest.mark.ac("AC-E1-S4-3")
def test_forbidden_precedes_not_found(env: Env, people: dict[str, int]) -> None:
    doctor = _headers(env.token(people["doc"], "DOCTOR"))
    assert env.client.get("/t/patient-object/10", headers=doctor).status_code == 403
    assert env.client.get("/t/patient-object/9999", headers=doctor).status_code == 403


@pytest.mark.ac("AC-E1-S4-3")
def test_ownership_foreign_object_is_not_found_identical_to_missing(
    env: Env, people: dict[str, int]
) -> None:
    owner = env.client.get("/t/patient-object/10", headers=_headers(env.token(people["p1"], "P")))
    assert owner.status_code == 200
    other = _headers(env.token(people["p2"], "PATIENT"))
    foreign = env.client.get("/t/patient-object/10", headers=other)
    missing = env.client.get("/t/patient-object/9999", headers=other)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.content == missing.content
    assert foreign.json()["code"] == "NOT_FOUND"


@pytest.mark.ac("AC-E1-S4-3")
def test_ownership_doctor_foreign_object_is_not_found(env: Env, people: dict[str, int]) -> None:
    other_doc = env.insert_staff("doc2@example.test", Role.DOCTOR)
    response = env.client.get(
        "/t/doctor-object/20", headers=_headers(env.token(other_doc, "DOCTOR"))
    )
    assert response.status_code == 404


@pytest.mark.ac("AC-E1-S4-4")
def test_deactivated_user_token_is_rejected_then_reactivated(
    env: Env, people: dict[str, int]
) -> None:
    token = env.login("p1@example.test")
    assert env.client.get("/api/auth/me", headers=_headers(token)).status_code == 200
    env.set_column(people["p1"], "active", 0)
    response = env.client.get("/api/auth/me", headers=_headers(token))
    assert response.status_code == 401 and response.json() == UNAUTH
    env.set_column(people["p1"], "active", 1)
    assert env.client.get("/api/auth/me", headers=_headers(token)).status_code == 200


@pytest.mark.ac("AC-E1-S4-4")
@pytest.mark.parametrize("user_id", [987654, 2**70])
def test_unknown_user_token_is_unauthenticated_not_500(env: Env, user_id: int) -> None:
    response = env.client.get("/api/auth/me", headers=_headers(env.token(user_id, "PATIENT")))
    assert response.status_code == 401 and response.json() == UNAUTH


@pytest.mark.ac("AC-E1-S4-4")
def test_zero_user_id_token_is_unauthenticated(env: Env) -> None:
    response = env.client.get("/api/auth/me", headers=_headers(env.token(0, "PATIENT")))
    assert response.status_code == 401


@pytest.mark.ac("AC-E1-S4-5")
def test_admin_reads_patient_doctor_and_admin_routes(env: Env, people: dict[str, int]) -> None:
    admin = _headers(env.token(people["admin"], "ADMIN"))
    for path in ("/t/admin", "/t/patient-object/10", "/t/doctor-object/20"):
        assert env.client.get(path, headers=admin).status_code == 200


@pytest.mark.ac("AC-E1-S4-5")
def test_admin_on_missing_object_is_not_found(env: Env, people: dict[str, int]) -> None:
    admin = _headers(env.token(people["admin"], "ADMIN"))
    assert env.client.get("/t/patient-object/9999", headers=admin).status_code == 404
    assert env.client.get("/t/doctor-object/9999", headers=admin).status_code == 404
