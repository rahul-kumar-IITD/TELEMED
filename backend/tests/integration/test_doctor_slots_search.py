"""E2-S3 (own slots, block/unblock) and E2-S4 (doctor search, open slots)."""
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from telemed.api.app import create_app
from telemed.repository.models import Slot, User
from telemed.service import security
from telemed.types.enums import Role
from tests.conftest import FrozenClock

PASSWORD = "Passw0rd!"
INITIAL = "Initial-Pw-9137"
NOW = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
TEMPLATES = [
    {"weekday": d, "start_time": "09:00", "end_time": "11:00", "slot_length_minutes": 30}
    for d in range(7)
]


def _iso(value: datetime) -> str:
    return quote(value.isoformat(), safe="")


def _z(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@pytest.fixture
def app(db_path: Path, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "UTC")
    return create_app(clock=frozen_clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _insert_user(engine: Engine, email: str, role: Role) -> None:
    with Session(engine) as session:
        session.add(
            User(email=email, password_hash=security.hash_password(PASSWORD), role=role.value,
                 active=1, created_at=NOW, updated_at=NOW)
        )
        session.commit()


def _login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(client: TestClient, engine: Engine) -> dict[str, str]:
    _insert_user(engine, "admin@example.test", Role.ADMIN)
    return _login(client, "admin@example.test")


@pytest.fixture
def patient(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json={
        "email": "p@example.test", "password": PASSWORD, "full_name": "P", "age": 30,
        "gender": "MALE", "phone": "1"})
    return _login(client, "p@example.test")


def _onboard(
    client: TestClient, admin: dict[str, str], email: str, name: str, specialty: str,
    languages: list[str], fee: str,
) -> dict[str, Any]:
    response = client.post("/api/admin/doctors", headers=admin, json={
        "email": email, "initial_password": INITIAL, "full_name": name, "specialty": specialty,
        "languages": languages, "fee": fee, "availability_templates": TEMPLATES})
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
def docs(client: TestClient, admin: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {
        "a": _onboard(client, admin, "a@example.test", "Zed Adams", "Cardiology",
                      ["hi", "en"], "300.00"),
        "b": _onboard(client, admin, "b@example.test", "amy Brown", "Dermatology", ["en"],
                      "750.00"),
        "c": _onboard(client, admin, "c@example.test", "Carl Cox", "Cardiology", ["en"],
                      "500.00"),
    }


@pytest.fixture
def doc_a(client: TestClient, docs: dict[str, dict[str, Any]]) -> dict[str, str]:
    return _login(client, "a@example.test", INITIAL)


def _slot_ids(engine: Engine, doctor_id: int) -> list[int]:
    stmt = select(Slot.slot_id).where(Slot.doctor_id == doctor_id).order_by(Slot.start_time)
    with Session(engine) as session:
        return [int(i) for i in session.scalars(stmt)]


def _status(engine: Engine, slot_id: int) -> str:
    with Session(engine) as session:
        row = session.get(Slot, slot_id)
        assert row is not None
        return row.status


def _set(engine: Engine, slot_id: int, **values: Any) -> None:
    with Session(engine) as session:
        session.execute(update(Slot).where(Slot.slot_id == slot_id).values(**values))
        session.commit()


def _set_active(engine: Engine, user_id: int, active: int) -> None:
    with Session(engine) as session:
        session.execute(update(User).where(User.user_id == user_id).values(active=active))
        session.commit()


def _block_all(engine: Engine, doctor_id: int, start: datetime, end: datetime) -> None:
    with Session(engine) as session:
        for slot in session.scalars(
            select(Slot).where(Slot.doctor_id == doctor_id, Slot.start_time >= start,
                               Slot.start_time <= end)
        ):
            slot.status = "BLOCKED"
        session.commit()


# ---------------- E2-S3 ----------------


@pytest.mark.ac("AC-E2-S3-1")
def test_my_slots_lists_only_own_in_range_ordered(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str], engine: Engine
) -> None:
    a_id = docs["a"]["doctor_id"]
    url = f"/api/doctors/me/slots?from={_iso(NOW)}&to={_iso(NOW + timedelta(days=2))}"
    response = client.get(url, headers=doc_a)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["items"]) > 0
    assert {i["doctor_id"] for i in body["items"]} == {a_id}
    starts = [i["start_time"] for i in body["items"]]
    assert starts == sorted(starts)
    assert all(_z(NOW) <= s <= _z(NOW + timedelta(days=2)) for s in starts)
    assert set(body["items"][0]) == {"slot_id", "doctor_id", "start_time", "end_time", "status"}
    blocked, booked = _slot_ids(engine, a_id)[:2]
    _set(engine, blocked, status="BLOCKED")
    _set(engine, booked, status="BOOKED")
    body = client.get(url, headers=doc_a).json()
    by_id = {i["slot_id"]: i["status"] for i in body["items"]}
    assert (by_id[blocked], by_id[booked]) == ("BLOCKED", "BOOKED")


@pytest.mark.ac("AC-E2-S3-1")
def test_my_slots_defaults_and_range_validation(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str]
) -> None:
    default = client.get("/api/doctors/me/slots", headers=doc_a)
    assert default.status_code == 200 and default.json()["total"] > 0
    only_from = client.get(
        f"/api/doctors/me/slots?from={_iso(NOW + timedelta(days=10))}", headers=doc_a
    )
    assert only_from.status_code == 200
    reversed_range = client.get(
        f"/api/doctors/me/slots?from={_iso(NOW + timedelta(days=1))}&to={_iso(NOW)}",
        headers=doc_a)
    assert reversed_range.status_code == 422
    assert reversed_range.json()["code"] == "VALIDATION_ERROR"
    too_long = client.get(
        f"/api/doctors/me/slots?from={_iso(NOW)}&to={_iso(NOW + timedelta(days=32))}",
        headers=doc_a)
    assert too_long.status_code == 422
    naive = client.get("/api/doctors/me/slots?from=2026-10-07T00:00:00", headers=doc_a)
    assert naive.status_code == 422


@pytest.mark.ac("AC-E2-S3-2")
def test_block_available_slot_then_block_again_conflicts(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str], engine: Engine
) -> None:
    a_id = docs["a"]["doctor_id"]
    slot = _slot_ids(engine, a_id)[0]
    response = client.put(f"/api/doctors/me/slots/{slot}/block", headers=doc_a)
    assert response.status_code == 200
    assert response.json()["slot_id"] == slot and response.json()["status"] == "BLOCKED"
    assert response.json()["doctor_id"] == a_id
    assert _status(engine, slot) == "BLOCKED"
    again = client.put(f"/api/doctors/me/slots/{slot}/block", headers=doc_a)
    assert again.status_code == 409 and again.json()["code"] == "INVALID_SLOT_STATE"


@pytest.mark.ac("AC-E2-S3-3")
def test_block_booked_slot_is_409_and_unchanged(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str], engine: Engine
) -> None:
    slot = _slot_ids(engine, docs["a"]["doctor_id"])[0]
    _set(engine, slot, status="BOOKED")
    response = client.put(f"/api/doctors/me/slots/{slot}/block", headers=doc_a)
    assert response.status_code == 409 and response.json()["code"] == "INVALID_SLOT_STATE"
    assert _status(engine, slot) == "BOOKED"


@pytest.mark.ac("AC-E2-S3-4")
def test_unblock_blocked_ok_and_non_blocked_conflicts(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str], engine: Engine
) -> None:
    first, second = _slot_ids(engine, docs["a"]["doctor_id"])[:2]
    _set(engine, first, status="BLOCKED")
    _set(engine, second, status="BOOKED")
    ok = client.put(f"/api/doctors/me/slots/{first}/unblock", headers=doc_a)
    assert ok.status_code == 200 and ok.json()["status"] == "AVAILABLE"
    assert _status(engine, first) == "AVAILABLE"
    for slot, expected in ((first, "AVAILABLE"), (second, "BOOKED")):
        response = client.put(f"/api/doctors/me/slots/{slot}/unblock", headers=doc_a)
        assert response.status_code == 409 and response.json()["code"] == "INVALID_SLOT_STATE"
        assert _status(engine, slot) == expected


@pytest.mark.ac("AC-E2-S3-5")
def test_foreign_or_missing_slot_is_404_before_409(
    client: TestClient, docs: dict[str, dict[str, Any]], doc_a: dict[str, str], engine: Engine
) -> None:
    b_slot = _slot_ids(engine, docs["b"]["doctor_id"])[0]
    for action in ("block", "unblock"):
        response = client.put(f"/api/doctors/me/slots/{b_slot}/{action}", headers=doc_a)
        assert response.status_code == 404 and response.json()["code"] == "NOT_FOUND"
    assert client.put("/api/doctors/me/slots/999999/block", headers=doc_a).status_code == 404
    _set(engine, b_slot, status="BOOKED")
    assert client.put(f"/api/doctors/me/slots/{b_slot}/block", headers=doc_a).status_code == 404
    _set(engine, b_slot, status="BLOCKED")
    assert client.put(f"/api/doctors/me/slots/{b_slot}/unblock", headers=doc_a).status_code == 404
    assert _status(engine, b_slot) == "BLOCKED"


@pytest.mark.ac("AC-E2-S3-5")
def test_patient_admin_and_anonymous_cannot_use_me_routes(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str],
    admin: dict[str, str], engine: Engine,
) -> None:
    slot = _slot_ids(engine, docs["a"]["doctor_id"])[0]
    for headers in (patient, admin):
        assert client.put(f"/api/doctors/me/slots/{slot}/block", headers=headers).status_code == 403
        assert client.put(
            f"/api/doctors/me/slots/{slot}/unblock", headers=headers
        ).status_code == 403
        assert client.get("/api/doctors/me/slots", headers=headers).status_code == 403
    assert client.put(f"/api/doctors/me/slots/{slot}/block").status_code == 401
    assert client.put(f"/api/doctors/me/slots/{slot}/unblock").status_code == 401
    assert client.get("/api/doctors/me/slots").status_code == 401
    assert _status(engine, slot) == "AVAILABLE"


# ---------------- E2-S4 ----------------


def _names(response: Any) -> list[str]:
    return [item["full_name"] for item in response.json()["items"]]


@pytest.mark.ac("AC-E2-S4-1")
@pytest.mark.ac("AC-02")
def test_filter_by_specialty_and_language(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str]
) -> None:
    both = client.get("/api/doctors?specialty=cardiology", headers=patient)
    assert sorted(_names(both)) == ["Carl Cox", "Zed Adams"] and both.json()["total"] == 2
    assert _names(client.get("/api/doctors?specialty=Nope", headers=patient)) == []
    hindi = client.get("/api/doctors?language=HI", headers=patient)
    assert _names(hindi) == ["Zed Adams"]
    combined = client.get("/api/doctors?specialty=Cardiology&language=en", headers=patient)
    assert len(combined.json()["items"]) == 2
    none = client.get("/api/doctors?specialty=Dermatology&language=hi", headers=patient)
    assert none.json() == {"items": [], "total": 0}


@pytest.mark.ac("AC-E2-S4-2")
def test_filter_by_availability_range(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str], engine: Engine
) -> None:
    day = NOW + timedelta(days=3)
    start, end = day.replace(hour=0), day.replace(hour=23, minute=59)
    _block_all(engine, docs["a"]["doctor_id"], start, end)
    url = f"/api/doctors?available_from={_iso(start)}&available_to={_iso(end)}"
    assert sorted(_names(client.get(url, headers=patient))) == ["Carl Cox", "amy Brown"]
    wide_end = _iso(end + timedelta(days=1))
    wide = f"/api/doctors?available_from={_iso(start)}&available_to={wide_end}"
    assert len(client.get(wide, headers=patient).json()["items"]) == 3
    only_from = client.get(
        f"/api/doctors?available_from={_iso(NOW + timedelta(days=100))}", headers=patient
    )
    assert only_from.json()["total"] == 0
    only_to = client.get(
        f"/api/doctors?available_to={_iso(NOW + timedelta(days=100))}", headers=patient
    )
    assert only_to.json()["total"] == 3
    bad = client.get(
        f"/api/doctors?available_from={_iso(end)}&available_to={_iso(start)}", headers=patient
    )
    assert bad.status_code == 422 and bad.json()["code"] == "VALIDATION_ERROR"
    naive = client.get("/api/doctors?available_from=2030-01-01T00:00:00", headers=patient)
    assert naive.status_code == 422


@pytest.mark.ac("AC-E2-S4-3")
def test_sorting(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str], engine: Engine
) -> None:
    _block_all(engine, docs["c"]["doctor_id"], NOW, NOW + timedelta(days=30))
    default = client.get("/api/doctors", headers=patient)
    explicit = client.get("/api/doctors?sort=earliest_slot", headers=patient)
    assert _names(default) == _names(explicit)
    assert _names(default)[-1] == "Carl Cox"  # no open slot sorts last
    assert default.json()["items"][-1]["earliest_slot"] is None
    assert _names(client.get("/api/doctors?sort=fee", headers=patient)) == [
        "Zed Adams", "Carl Cox", "amy Brown"]
    assert _names(client.get("/api/doctors?sort=name", headers=patient)) == [
        "amy Brown", "Carl Cox", "Zed Adams"]
    assert client.get("/api/doctors?sort=bogus", headers=patient).status_code == 422


@pytest.mark.ac("AC-E2-S4-4")
def test_summary_shape_fee_string_earliest_and_deactivated_hidden(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str], engine: Engine
) -> None:
    a_id = docs["a"]["doctor_id"]
    response = client.get("/api/doctors", headers=patient)
    item = next(i for i in response.json()["items"] if i["doctor_id"] == a_id)
    assert set(item) == {"doctor_id", "full_name", "specialty", "languages", "fee",
                         "earliest_slot"}
    assert item["fee"] == "300.00" and item["languages"] == ["hi", "en"]
    with Session(engine) as session:
        first = session.get(Slot, _slot_ids(engine, a_id)[0])
        assert first is not None
        expected = first.start_time
    assert item["earliest_slot"] == _z(expected)
    detail = client.get(f"/api/doctors/{a_id}", headers=patient)
    assert detail.status_code == 200 and detail.json() == item
    c_id = docs["c"]["doctor_id"]
    _set_active(engine, c_id, 0)
    assert "Carl Cox" not in _names(client.get("/api/doctors", headers=patient))
    assert client.get(f"/api/doctors/{c_id}", headers=patient).status_code == 404
    assert client.get(f"/api/doctors/{c_id}/slots", headers=patient).status_code == 404


@pytest.mark.ac("AC-E2-S4-5")
@pytest.mark.ac("AC-03")
def test_open_slots_only_available_future_within_14_days(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str], engine: Engine
) -> None:
    a_id = docs["a"]["doctor_id"]
    ids = _slot_ids(engine, a_id)
    booked, blocked, past, far = ids[0], ids[1], ids[2], ids[3]
    _set(engine, booked, status="BOOKED")
    _set(engine, blocked, status="BLOCKED")
    _set(engine, past, start_time=NOW - timedelta(hours=1), end_time=NOW)
    _set(engine, far, start_time=NOW + timedelta(days=15),
         end_time=NOW + timedelta(days=15, hours=1))
    response = client.get(f"/api/doctors/{a_id}/slots", headers=patient)
    assert response.status_code == 200
    body = response.json()
    got = [i["slot_id"] for i in body["items"]]
    assert body["total"] == len(got) == len(ids) - 4
    assert not {booked, blocked, past, far} & set(got)
    assert {i["status"] for i in body["items"]} == {"AVAILABLE"}
    starts = [i["start_time"] for i in body["items"]]
    assert starts == sorted(starts)


@pytest.mark.ac("AC-E2-S4-5")
def test_open_slots_unknown_or_non_doctor_is_404_and_roles_allowed(
    client: TestClient, docs: dict[str, dict[str, Any]], patient: dict[str, str],
    admin: dict[str, str], doc_a: dict[str, str],
) -> None:
    assert client.get("/api/doctors/999999/slots", headers=patient).status_code == 404
    assert client.get("/api/doctors/999999", headers=patient).status_code == 404
    patient_id = client.get("/api/auth/me", headers=patient).json()["user_id"]
    assert client.get(f"/api/doctors/{patient_id}/slots", headers=patient).status_code == 404
    a_id = docs["a"]["doctor_id"]
    for headers in (doc_a, admin):
        assert client.get("/api/doctors", headers=headers).status_code == 200
        assert client.get(f"/api/doctors/{a_id}/slots", headers=headers).status_code == 200


@pytest.mark.ac("AC-E2-S4-6")
def test_anonymous_and_garbage_tokens_get_401(
    client: TestClient, docs: dict[str, dict[str, Any]]
) -> None:
    a_id = docs["a"]["doctor_id"]
    garbage = {"Authorization": "Bearer junk"}
    for path in ("/api/doctors", f"/api/doctors/{a_id}", f"/api/doctors/{a_id}/slots",
                 "/api/doctors/me/slots"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=garbage).status_code == 401
