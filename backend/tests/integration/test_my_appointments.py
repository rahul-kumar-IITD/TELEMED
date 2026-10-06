"""E4-S3: patient appointment list, detail access, 60-minute rule and join_url."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.conftest import FrozenClock
from tests.integration.conftest import (
    NOW,
    Doctor,
    Headers,
    book_at,
    onboard,
    register,
    set_status,
    slot_ids,
)

LIVE = ("BOOKED", "CHECKED_IN", "IN_PROGRESS")
DONE = ("COMPLETED", "CANCELLED", "NO_SHOW")


@pytest.mark.ac("E4-S3-AC1")
def test_mine_scoped_ordered_and_filtered(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    other = register(client, "p2@example.test")
    later, _ = book_at(client, engine, doctor[0], patient, NOW + timedelta(days=3))
    sooner, _ = book_at(client, engine, doctor[0], patient, NOW + timedelta(days=1))
    theirs, _ = book_at(client, engine, doctor[0], other, NOW + timedelta(days=2))
    set_status(engine, later, "CANCELLED")
    body = client.get("/api/appointments/mine", headers=patient).json()
    assert [i["appointment_id"] for i in body["items"]] == [sooner, later]
    assert body["total"] == 2 and theirs not in [i["appointment_id"] for i in body["items"]]
    item = body["items"][0]
    assert item["fee"] == "500.00" and item["doctor"]["full_name"] == "Dr Rao"
    assert isinstance(item["allowed_actions"], list) and item["status"] == "BOOKED"
    only = client.get("/api/appointments/mine?status=CANCELLED", headers=patient).json()
    assert [i["appointment_id"] for i in only["items"]] == [later] and only["total"] == 1
    assert client.get("/api/appointments/mine?status=BOGUS", headers=patient).status_code == 422
    fresh = register(client, "p3@example.test")
    assert client.get("/api/appointments/mine", headers=fresh).json() == {"items": [], "total": 0}
    assert client.get("/api/appointments/mine", headers=doctor[1]).status_code == 403
    assert client.get("/api/appointments/mine", headers=admin).status_code == 403
    assert client.get("/api/appointments/mine").status_code == 401


@pytest.mark.ac("E4-S3-AC2")
def test_detail_access_by_role(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    appt, _ = book_at(client, engine, doctor[0], patient, NOW + timedelta(hours=5))
    _, other_doctor = onboard(client, admin, "d2@example.test")
    other_patient = register(client, "p2@example.test")
    url = f"/api/appointments/{appt}"
    for who in (patient, doctor[1], admin):
        response = client.get(url, headers=who)
        assert response.status_code == 200
        assert response.json()["appointment_id"] == appt
    assert client.get(url, headers=admin).json()["allowed_actions"] == []
    assert client.get(url, headers=admin).json()["join_url"] is None
    assert client.get(url, headers=other_patient).status_code == 404
    assert client.get(url, headers=other_doctor).status_code == 404
    assert client.get("/api/appointments/99999", headers=admin).status_code == 404
    assert client.get(url).status_code == 401


@pytest.mark.ac("E4-S3-AC3")
def test_sixty_minute_boundary_with_injected_clock(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers,
    frozen_clock: FrozenClock,
) -> None:
    appt, _ = book_at(client, engine, doctor[0], patient, NOW + timedelta(minutes=60))

    def actions() -> tuple[list[str], list[str]]:
        detail = client.get(f"/api/appointments/{appt}", headers=patient).json()
        mine = client.get("/api/appointments/mine", headers=patient).json()["items"][0]
        return detail["allowed_actions"], mine["allowed_actions"]

    assert actions() == (["CANCEL", "RESCHEDULE"], ["CANCEL", "RESCHEDULE"])
    detail = client.get(f"/api/appointments/{appt}", headers=patient).json()
    assert datetime.fromisoformat(detail["change_deadline"]) == NOW  # start - 60 min
    frozen_clock.advance(timedelta(seconds=1))
    assert actions() == ([], [])
    frozen_clock.advance(timedelta(hours=-1))
    set_status(engine, appt, "CANCELLED")
    assert actions() == ([], [])


@pytest.mark.ac("E4-S3-AC4")
@pytest.mark.parametrize("status", LIVE + DONE)
def test_join_url_by_status(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers,
    status: str,
) -> None:
    appt, _ = book_at(client, engine, doctor[0], patient, NOW + timedelta(hours=5))
    set_status(engine, appt, status)
    url = f"/api/appointments/{appt}"
    mine = client.get("/api/appointments/mine", headers=patient).json()["items"][0]
    seen = [client.get(url, headers=patient).json()["join_url"],
            client.get(url, headers=doctor[1]).json()["join_url"], mine["join_url"]]
    for join_url in seen:
        if status in LIVE:
            assert isinstance(join_url, str) and str(appt) in join_url
        else:
            assert join_url is None
    assert client.get(url, headers=admin).json()["join_url"] is None


@pytest.mark.ac("E4-S3-AC4")
def test_booking_response_has_join_url(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    response = client.post("/api/appointments", headers=patient,
                           json={"slot_id": slot_ids(engine, doctor[0], 1)[0]})
    assert response.json()["join_url"]
