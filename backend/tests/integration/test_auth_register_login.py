"""E1-S3: patient registration and login (API-03, API-04)."""
import io
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.config.logging import configure_logging
from telemed.repository.models import PatientProfileVersion, User
from tests.conftest import FrozenClock

PASSWORD = "Passw0rd!"
GENERIC_401 = {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}


def _body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "email": "p1@example.test",
        "password": PASSWORD,
        "full_name": "Pat One",
        "age": 34,
        "gender": "FEMALE",
        "phone": "+911234567890",
    }
    body.update(overrides)
    return body


@pytest.fixture
def clock(frozen_clock: FrozenClock) -> FrozenClock:
    return frozen_clock


@pytest.fixture
def client(
    db_path: Path, engine: Engine, clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    with TestClient(create_app(clock=clock)) as test_client:
        yield test_client


def _counts(engine: Engine) -> tuple[int, int]:
    with Session(engine) as session:
        users = session.scalar(select(func.count()).select_from(User))
        versions = session.scalar(select(func.count()).select_from(PatientProfileVersion))
        return int(users or 0), int(versions or 0)


@pytest.mark.ac("AC-E1-S3-1")
@pytest.mark.ac("AC-01")
def test_register_returns_201_without_secrets(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=_body())
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"user_id", "role", "email"}
    assert isinstance(body["user_id"], int)
    assert body["role"] == "PATIENT"
    assert body["email"] == "p1@example.test"
    assert PASSWORD not in response.text and "argon2" not in response.text


@pytest.mark.ac("AC-E1-S3-2")
def test_role_in_body_is_ignored(client: TestClient, engine: Engine) -> None:
    response = client.post(
        "/api/auth/register", json=_body(email="p2@example.test", role="ADMIN")
    )
    assert response.status_code == 201
    assert response.json()["role"] == "PATIENT"
    with Session(engine) as session:
        assert session.scalar(select(User.role).where(User.email == "p2@example.test")) == "PATIENT"


@pytest.mark.ac("AC-E1-S3-3")
def test_duplicate_email_is_case_insensitive_409(client: TestClient, engine: Engine) -> None:
    first = client.post("/api/auth/register", json=_body(email="Mixed@Example.TEST"))
    assert first.status_code == 201
    response = client.post("/api/auth/register", json=_body(email="MIXED@example.test"))
    assert response.status_code == 409
    assert response.json() == {
        "code": "EMAIL_ALREADY_REGISTERED",
        "message": "That email is already registered.",
    }
    with Session(engine) as session:
        assert session.scalars(select(User.email)).all() == ["mixed@example.test"]
    assert _counts(engine) == (1, 1)


@pytest.mark.ac("AC-E1-S3-4")
@pytest.mark.parametrize(("length", "status"), [(7, 422), (8, 201), (128, 201), (129, 422)])
def test_password_length_bounds(client: TestClient, length: int, status: int) -> None:
    response = client.post("/api/auth/register", json=_body(password="a" * length))
    assert response.status_code == status
    if status == 422:
        assert [e["field"] for e in response.json()["errors"]] == ["password"]


@pytest.mark.ac("AC-E1-S3-5")
def test_stored_hash_is_argon2(client: TestClient, engine: Engine) -> None:
    client.post("/api/auth/register", json=_body())
    with Session(engine) as session:
        stored = session.scalar(select(User.password_hash).where(User.email == "p1@example.test"))
    assert stored is not None and stored.startswith("$argon2") and stored != PASSWORD


@pytest.mark.ac("AC-E1-S3-6")
def test_login_success_returns_token(client: TestClient, clock: FrozenClock) -> None:
    user_id = client.post("/api/auth/register", json=_body()).json()["user_id"]
    response = client.post(
        "/api/auth/login", json={"email": "P1@example.test", "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "PATIENT" and body["user_id"] == user_id
    assert len(body["access_token"].split(".")) == 3
    assert body["expires_in"] == 1800
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at == clock.now() + timedelta(seconds=1800)
    assert body["expires_at"].endswith("Z") and expires_at.tzinfo == UTC


@pytest.mark.ac("AC-E1-S3-6")
def test_all_login_failures_are_byte_identical(client: TestClient, engine: Engine) -> None:
    client.post("/api/auth/register", json=_body())
    client.post("/api/auth/register", json=_body(email="p2@example.test"))
    with Session(engine) as session, session.begin():
        user = session.scalars(select(User).where(User.email == "p2@example.test")).one()
        user.active = 0
    attempts = [
        {"email": "p1@example.test", "password": "wrong-password"},
        {"email": "nobody@example.test", "password": PASSWORD},
        {"email": "p2@example.test", "password": PASSWORD},
    ]
    responses = [client.post("/api/auth/login", json=attempt) for attempt in attempts]
    assert [r.status_code for r in responses] == [401, 401, 401]
    assert len({r.content for r in responses}) == 1
    assert responses[0].json() == GENERIC_401


@pytest.mark.ac("AC-E1-S3-6")
def test_login_requires_both_fields(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "p1@example.test"})
    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == ["password"]
    assert client.post(
        "/api/auth/login", json={"email": "p1@example.test", "password": ""}
    ).status_code == 422


@pytest.mark.ac("AC-E1-S3-7")
def test_initial_profile_is_version_one(client: TestClient, engine: Engine) -> None:
    user_id = client.post("/api/auth/register", json=_body()).json()["user_id"]
    with Session(engine) as session:
        rows = session.scalars(select(PatientProfileVersion)).all()
    assert len(rows) == 1
    row = rows[0]
    assert (row.patient_id, row.version_number, row.changed_by_user_id) == (user_id, 1, user_id)
    assert (row.full_name, row.age, row.gender, row.phone) == (
        "Pat One", 34, "FEMALE", "+911234567890",
    )


@pytest.mark.ac("AC-E1-S3-7")
@pytest.mark.parametrize("field", ["full_name", "age", "gender", "phone"])
def test_missing_profile_field_is_422_and_creates_nothing(
    client: TestClient, engine: Engine, field: str
) -> None:
    body = _body()
    del body[field]
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert [e["field"] for e in response.json()["errors"]] == [field]
    assert _counts(engine) == (0, 0)


@pytest.mark.ac("AC-E1-S3-7")
@pytest.mark.parametrize(
    ("age", "status"),
    [(0, 422), (131, 422), (-1, 422), (30.5, 422), ("30", 422), (True, 422), (1, 201), (130, 201)],
)
def test_age_validation(client: TestClient, age: object, status: int) -> None:
    response = client.post("/api/auth/register", json=_body(age=age))
    assert response.status_code == status
    if status == 422:
        assert [e["field"] for e in response.json()["errors"]] == ["age"]


@pytest.mark.ac("AC-E1-S3-7")
@pytest.mark.parametrize(
    ("gender", "status"),
    [("ROBOT", 422), ("female", 422), ("FEMALE", 201), ("MALE", 201), ("OTHER", 201),
     ("UNDISCLOSED", 201)],
)
def test_gender_validation(client: TestClient, gender: str, status: int) -> None:
    response = client.post("/api/auth/register", json=_body(gender=gender))
    assert response.status_code == status
    if status == 422:
        assert [e["field"] for e in response.json()["errors"]] == ["gender"]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"email": "not-an-email"}, "email"),
        ({"email": "a" * 250 + "@x.test"}, "email"),
        ({"full_name": "   "}, "full_name"),
        ({"full_name": "x" * 201}, "full_name"),
        ({"phone": " "}, "phone"),
        ({"phone": "1" * 33}, "phone"),
    ],
)
def test_other_field_validation(client: TestClient, overrides: dict[str, Any], field: str) -> None:
    response = client.post("/api/auth/register", json=_body(**overrides))
    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == [field]


def test_register_logs_no_phi_or_password(client: TestClient) -> None:
    stream = io.StringIO()
    root = logging.getLogger()
    saved, level = list(root.handlers), root.level
    configure_logging(stream=stream)
    try:
        client.post("/api/auth/register", json=_body())
        client.post("/api/auth/login", json={"email": "p1@example.test", "password": PASSWORD})
    finally:
        root.handlers[:] = saved
        root.setLevel(level)
    raw = stream.getvalue()
    for secret in (PASSWORD, "p1@example.test", "Pat One", "+911234567890", "argon2"):
        assert secret not in raw
