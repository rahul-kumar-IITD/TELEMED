"""E4-S1: append-only consultation notes (API-27..29)."""
import io
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from telemed.config.logging import configure_logging
from tests.integration.conftest import (
    Doctor,
    Headers,
    book,
    onboard,
    register,
    set_status,
    slot_ids,
)

Done = tuple[int, Headers, Headers]  # appointment id, patient headers, doctor headers


@pytest.fixture
def completed(engine: Engine, doctor: Doctor, patient: Headers, client: TestClient) -> Done:
    appt = book(client, patient, slot_ids(engine, doctor[0], 1)[0])
    set_status(engine, appt, "COMPLETED")
    return appt, patient, doctor[1]


def _count(engine: Engine) -> int:
    with Session(engine) as session:
        return int(session.execute(text("SELECT count(*) FROM consultation_notes")).scalar_one())


@pytest.mark.ac("E4-S1-AC1")
@pytest.mark.ac("AC-09")
def test_doctor_appends_notes_which_accumulate(
    client: TestClient, engine: Engine, completed: Done
) -> None:
    appt, _, doc = completed
    first = client.post(f"/api/appointments/{appt}/notes", headers=doc, json={"text": "note one"})
    second = client.post(f"/api/appointments/{appt}/notes", headers=doc, json={"text": "note two"})
    assert (first.status_code, second.status_code) == (201, 201)
    body = first.json()
    assert set(body) == {"note_id", "appointment_id", "author_id", "text", "created_at"}
    assert (body["appointment_id"], body["text"]) == (appt, "note one")
    assert second.json()["note_id"] > body["note_id"]
    listing = client.get(f"/api/appointments/{appt}/notes", headers=doc).json()
    assert [n["text"] for n in listing["items"]] == ["note one", "note two"]
    assert listing["total"] == 2
    assert _count(engine) == 2


@pytest.mark.ac("E4-S1-AC2")
@pytest.mark.parametrize("status", ["BOOKED", "CHECKED_IN", "IN_PROGRESS", "CANCELLED", "NO_SHOW"])
def test_note_on_non_completed_is_409(
    client: TestClient, engine: Engine, completed: Done, status: str
) -> None:
    appt, patient, doc = completed
    set_status(engine, appt, status)
    response = client.post(f"/api/appointments/{appt}/notes", headers=doc, json={"text": "x"})
    assert (response.status_code, response.json()["code"]) == (409, "INVALID_APPOINTMENT_STATE")
    assert client.post(
        f"/api/appointments/{appt}/notes", headers=patient, json={"text": "x"}
    ).status_code == 403
    assert _count(engine) == 0


@pytest.mark.ac("E4-S1-AC2")
def test_note_access_by_other_roles(
    client: TestClient, engine: Engine, admin: Headers, completed: Done
) -> None:
    appt, patient, _ = completed
    _, other_doctor = onboard(client, admin, "d2@example.test")
    url = f"/api/appointments/{appt}/notes"
    assert client.post(url, headers=other_doctor, json={"text": "x"}).status_code == 404
    assert client.post(url, headers=patient, json={"text": "x"}).status_code == 403
    assert client.post(url, headers=admin, json={"text": "x"}).status_code == 403
    assert client.post(url, json={"text": "x"}).status_code == 401
    missing = client.post("/api/appointments/99999/notes", headers=other_doctor, json={"text": "x"})
    assert missing.status_code == 404
    assert _count(engine) == 0


@pytest.mark.ac("E4-S1-AC3")
def test_text_length_boundaries(client: TestClient, engine: Engine, completed: Done) -> None:
    appt, _, doc = completed
    exact = "a" * 5000
    unicode_text = "é中" * 2500  # 5000 characters, 10000 bytes
    for accepted in (exact, unicode_text):
        response = client.post(f"/api/appointments/{appt}/notes", headers=doc,
                               json={"text": accepted})
        assert response.status_code == 201
        assert response.json()["text"] == accepted
    for bad in ("a" * 5001, "", "   \n\t ", 123, None):
        response = client.post(f"/api/appointments/{appt}/notes", headers=doc,
                               json={"text": bad})
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    assert client.post(f"/api/appointments/{appt}/notes", headers=doc, json={}).status_code == 422
    assert _count(engine) == 2


@pytest.mark.ac("E4-S1-AC4")
@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
@pytest.mark.nfr("NFR-08")
def test_note_mutation_methods_are_405(
    client: TestClient, engine: Engine, completed: Done, method: str
) -> None:
    appt, _, doc = completed
    note = client.post(f"/api/appointments/{appt}/notes", headers=doc, json={"text": "keep"}).json()
    response = client.request(
        method, f"/api/appointments/{appt}/notes/{note['note_id']}", headers=doc,
        json={"text": "changed"},
    )
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["Allow"]
    with Session(engine) as session:
        stored = session.execute(text("SELECT text FROM consultation_notes")).scalar_one()
    assert stored == "keep"


@pytest.mark.ac("E4-S1-AC5")
def test_read_access_and_scoping(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, completed: Done
) -> None:
    appt, patient, doc = completed
    note = client.post(f"/api/appointments/{appt}/notes", headers=doc, json={"text": "n"}).json()
    list_url = f"/api/appointments/{appt}/notes"
    one_url = f"{list_url}/{note['note_id']}"
    for who in (patient, doc, admin):
        listing = client.get(list_url, headers=who)
        assert (listing.status_code, listing.json()["total"]) == (200, 1)
        assert client.get(one_url, headers=who).json()["note_id"] == note["note_id"]
    _, other_doctor = onboard(client, admin, "d2@example.test")
    other_patient = register(client, "p2@example.test")
    for who in (other_patient, other_doctor):
        assert client.get(list_url, headers=who).status_code == 404
        assert client.get(one_url, headers=who).status_code == 404
    assert client.get("/api/appointments/99999/notes", headers=admin).status_code == 404
    assert client.get(list_url).status_code == 401
    # a note id from another appointment is not reachable through this appointment
    second = book(client, patient, slot_ids(engine, doctor[0], 1)[0])
    assert client.get(f"/api/appointments/{second}/notes/{note['note_id']}",
                      headers=doc).status_code == 404
    assert client.get(f"/api/appointments/{second}/notes", headers=doc).json() == {
        "items": [], "total": 0}


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield buffer
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


@pytest.mark.ac("E4-S1-AC6")
def test_note_post_logs_ids_never_text(
    client: TestClient, completed: Done, log_stream: io.StringIO
) -> None:
    appt, _, doc = completed
    configure_logging(stream=log_stream)
    marker = "PHIMARKER-7f3a9c21"
    ok = client.post(f"/api/appointments/{appt}/notes", headers=doc,
                     json={"text": f"visit {marker}"})
    bad = client.post(f"/api/appointments/{appt}/notes", headers=doc,
                      json={"text": marker * 600})
    assert (ok.status_code, bad.status_code) == (201, 422)
    raw = log_stream.getvalue()
    assert marker not in raw
    lines = [json.loads(line) for line in raw.splitlines() if line.strip()]
    added = [line for line in lines if line["event"] == "note_added"]
    assert len(added) == 1
    assert added[0]["appointment_id"] == appt
    assert "user_id" in added[0]
