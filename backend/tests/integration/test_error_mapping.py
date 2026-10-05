"""E1-S2 AC4: exception -> status mapping with flat generic bodies."""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AwareDatetime, BaseModel
from sqlalchemy.exc import OperationalError

from telemed.api.app import create_app
from telemed.types.errors import (
    DomainError,
    InvalidAppointmentStateException,
    SlotUnavailableException,
)

PHI = "secret-phi-value"


class Payload(BaseModel):
    when: AwareDatetime
    count: int


def _lock_error() -> sqlite3.OperationalError:
    return sqlite3.OperationalError("database is locked")


@pytest.fixture
def app() -> FastAPI:
    app = create_app()

    @app.get("/t/slot")
    async def slot() -> None:
        raise SlotUnavailableException(PHI)

    @app.get("/t/state")
    async def state() -> None:
        raise InvalidAppointmentStateException(PHI)

    @app.get("/t/domain")
    async def domain() -> None:
        raise DomainError(PHI)

    @app.post("/t/body")
    async def body(payload: Payload) -> dict[str, int]:
        return {"count": payload.count}

    @app.get("/t/locked")
    async def locked() -> None:
        raise OperationalError("UPDATE slots ...", {}, _lock_error())

    @app.get("/t/raw-locked")
    async def raw_locked() -> None:
        raise _lock_error()

    @app.get("/t/other-db-error")
    async def other_db_error() -> None:
        raise OperationalError("SELECT ...", {}, sqlite3.OperationalError("no such table: x"))

    @app.get("/t/boom")
    async def boom() -> None:
        raise RuntimeError(PHI)

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.ac("AC-E1-S2-4")
def test_slot_unavailable_is_409(client: TestClient) -> None:
    response = client.get("/t/slot")
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_UNAVAILABLE"
    assert PHI not in response.text
    assert "X-Request-ID" in response.headers


@pytest.mark.ac("AC-E1-S2-4")
def test_invalid_state_is_409(client: TestClient) -> None:
    response = client.get("/t/state")
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_APPOINTMENT_STATE"
    assert PHI not in response.text


def test_unmapped_domain_error_is_generic_500(client: TestClient) -> None:
    response = client.get("/t/domain")
    assert response.status_code == 500
    assert PHI not in response.text


@pytest.mark.ac("AC-E1-S2-4")
def test_naive_datetime_is_422_without_echo(client: TestClient) -> None:
    response = client.post("/t/body", json={"when": "2026-10-12T03:30:00", "count": 1})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "when"
    assert "2026-10-12" not in response.text


@pytest.mark.ac("AC-E1-S2-4")
def test_malformed_input_is_422(client: TestClient) -> None:
    response = client.post("/t/body", json={"when": "2026-10-12T03:30:00Z", "count": PHI})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "count"
    assert PHI not in response.text
    assert client.post("/t/body", content="not json", headers={"content-type": "application/json"}
                       ).status_code == 422


@pytest.mark.ac("AC-E1-S2-4")
@pytest.mark.parametrize("path", ["/t/locked", "/t/raw-locked"])
def test_lock_timeout_is_503_generic(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 503
    assert response.json() == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "The service is busy, please try again.",
    }
    assert "X-Request-ID" in response.headers


@pytest.mark.ac("AC-E1-S2-4")
def test_real_sqlite_lock_timeout_is_recognised(tmp_path: Path) -> None:
    from telemed.service.bootstrap import is_lock_timeout

    path = tmp_path / "lock.db"
    holder = sqlite3.connect(path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    waiter = sqlite3.connect(path, isolation_level=None, timeout=0.05)
    with pytest.raises(sqlite3.OperationalError) as caught:
        waiter.execute("BEGIN IMMEDIATE")
    assert is_lock_timeout(caught.value)
    holder.close()
    waiter.close()


def test_other_errors_are_generic_500(client: TestClient) -> None:
    for path in ("/t/other-db-error", "/t/boom"):
        response = client.get(path)
        assert response.status_code == 500
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert PHI not in response.text and "no such table" not in response.text


def test_404_and_405_bodies_are_flat(client: TestClient) -> None:
    assert client.get("/nope").json()["code"] == "NOT_FOUND"
    assert client.post("/health").json()["code"] == "METHOD_NOT_ALLOWED"
