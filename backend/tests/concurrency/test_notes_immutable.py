"""E4-S1 AC4: notes cannot be changed or removed, even by direct SQL or concurrent writers."""
# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from tests.integration.conftest import (  # noqa: F401 - fixtures re-exported for this package
    Doctor,
    Headers,
    admin,
    app,
    book,
    client,
    doctor,
    patient,
    payment,
    provider_tz,
    set_status,
    slot_ids,
)


@pytest.fixture
def note(client: TestClient, engine: Engine, doctor: Doctor, patient: Headers) -> tuple[int, int]:
    appt = book(client, patient, slot_ids(engine, doctor[0], 1)[0])
    set_status(engine, appt, "COMPLETED")
    response = client.post(f"/api/appointments/{appt}/notes", headers=doctor[1],
                           json={"text": "original"})
    return appt, int(response.json()["note_id"])


def _stored(engine: Engine) -> list[str]:
    with Session(engine) as session:
        return [r[0] for r in session.execute(text("SELECT text FROM consultation_notes"))]


@pytest.mark.ac("E4-S1-AC4")
@pytest.mark.parametrize(
    "sql", ["UPDATE consultation_notes SET text = 'hacked'", "DELETE FROM consultation_notes"]
)
def test_direct_sql_is_rejected_by_trigger(engine: Engine, note: tuple[int, int], sql: str) -> None:
    with Session(engine) as session, pytest.raises(DatabaseError, match="append-only"):
        session.execute(text(sql))
    assert _stored(engine) == ["original"]


@pytest.mark.ac("E4-S1-AC4")
def test_concurrent_mutation_attempts_never_change_the_note(
    client: TestClient, engine: Engine, doctor: Doctor, note: tuple[int, int]
) -> None:
    appt, note_id = note
    url = f"/api/appointments/{appt}/notes/{note_id}"
    methods = ["PUT", "PATCH", "DELETE"] * 4

    def attempt(method: str) -> int:
        return client.request(method, url, headers=doctor[1], json={"text": "x"}).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(attempt, methods))
    assert set(statuses) == {405}
    assert _stored(engine) == ["original"]
