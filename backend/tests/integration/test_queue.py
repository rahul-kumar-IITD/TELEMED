"""E3-S5: doctor daily queue (API-15) in the provider timezone."""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.integration.conftest import (
    Doctor,
    Headers,
    book,
    onboard,
    register,
    set_slot_start,
    set_status,
    slot_ids,
)


@pytest.fixture
def provider_tz() -> str:
    return "Asia/Kolkata"


@pytest.mark.ac("E3-S5-AC4")
def test_queue_day_boundary_order_and_scope(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    first, second, third, fourth = slot_ids(engine, doctor[0], 4)
    # IST is UTC+5:30: 18:00Z = 23:30 IST on 10-08, 19:00Z = 00:30 IST on 10-09
    set_slot_start(engine, first, datetime(2026, 10, 8, 19, 0, tzinfo=UTC))
    set_slot_start(engine, second, datetime(2026, 10, 8, 18, 0, tzinfo=UTC))
    set_slot_start(engine, third, datetime(2026, 10, 8, 18, 30, tzinfo=UTC))  # 00:00 IST 10-09
    set_slot_start(engine, fourth, datetime(2026, 10, 8, 18, 29, tzinfo=UTC))  # 23:59 IST 10-08
    p2 = register(client, "q@example.test")
    appts = [book(client, patient, s) for s in (first, second, third, fourth)]
    set_status(engine, appts[3], "CANCELLED")
    other_id, other = onboard(client, admin, "d2@example.test")
    book(client, p2, slot_ids(engine, other_id, 1)[0])

    day1 = client.get("/api/doctors/me/queue?date=2026-10-08", headers=doctor[1]).json()
    assert (day1["date"], day1["timezone"], day1["total"]) == ("2026-10-08", "Asia/Kolkata", 2)
    assert [i["appointment_id"] for i in day1["items"]] == [appts[1], appts[3]]
    assert day1["items"][1]["status"] == "CANCELLED"
    assert day1["items"][0]["allowed_actions"] == ["CHECKED_IN", "CANCEL"]
    day2 = client.get("/api/doctors/me/queue?date=2026-10-09", headers=doctor[1]).json()
    assert [i["appointment_id"] for i in day2["items"]] == [appts[2], appts[0]]
    assert client.get("/api/doctors/me/queue?date=2026-10-09", headers=other).json()["total"] == 0


@pytest.mark.ac("E3-S5-AC4")
def test_default_date_is_today_in_provider_zone(client: TestClient, doctor: Doctor) -> None:
    # frozen clock is 2026-10-06 00:00Z = 05:30 IST the same day
    response = client.get("/api/doctors/me/queue", headers=doctor[1])
    assert response.status_code == 200
    body = response.json()
    assert (body["date"], body["items"], body["total"]) == ("2026-10-06", [], 0)


@pytest.mark.ac("E3-S5-AC4")
def test_queue_validation_and_roles(
    client: TestClient, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    assert client.get("/api/doctors/me/queue?date=nope", headers=doctor[1]).status_code == 422
    assert client.get("/api/doctors/me/queue", headers=patient).status_code == 403
    assert client.get("/api/doctors/me/queue", headers=admin).status_code == 403
    assert client.get("/api/doctors/me/queue").status_code == 401
