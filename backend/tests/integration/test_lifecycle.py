"""E3-S5: doctor lifecycle transitions (API-26) and role-scoped GET (API-23)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine

from tests.conftest import SpyPayment
from tests.integration.conftest import (
    NOW,
    Doctor,
    Headers,
    appt_row,
    book_at,
    events,
    onboard,
    register,
    set_slot_start,
    set_status,
    slot_status,
)


def _status(client: TestClient, headers: Headers | None, appt: int, status: str) -> Response:
    return client.post(
        f"/api/appointments/{appt}/status", headers=headers or {}, json={"status": status}
    )


def _booked(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers,
    lead: timedelta = timedelta(hours=3),
) -> tuple[int, int]:
    return book_at(client, engine, doctor[0], patient, NOW + lead)


@pytest.mark.ac("E3-S5-AC1")
def test_full_happy_path_one_doctor_event_per_transition(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, _ = _booked(client, engine, doctor, patient)
    for count, target in enumerate(["CHECKED_IN", "IN_PROGRESS", "COMPLETED"], start=2):
        response = _status(client, doctor[1], appt, target)
        assert response.status_code == 200
        assert response.json()["status"] == target
        log = events(engine, appt)
        assert len(log) == count
        assert (log[-1].event_type, log[-1].actor_role) == (target, "DOCTOR")
    assert response.json()["allowed_actions"] == []
    assert response.json()["join_url"] is None


@pytest.mark.ac("E3-S5-AC2")
@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("BOOKED", "IN_PROGRESS"), ("BOOKED", "COMPLETED"), ("BOOKED", "BOOKED"),
        ("CHECKED_IN", "CANCELLED"), ("CHECKED_IN", "BOOKED"),
        ("COMPLETED", "IN_PROGRESS"), ("CANCELLED", "CHECKED_IN"), ("NO_SHOW", "COMPLETED"),
    ],
)
def test_invalid_transitions_409_no_event(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, current: str,
    target: str,
) -> None:
    appt, _ = _booked(client, engine, doctor, patient)
    set_status(engine, appt, current)
    response = _status(client, doctor[1], appt, target)
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_APPOINTMENT_STATE"
    assert appt_row(engine, appt).status == current
    assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S5-AC2")
def test_unknown_status_is_422(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, _ = _booked(client, engine, doctor, patient)
    assert _status(client, doctor[1], appt, "FLYING").status_code == 422


@pytest.mark.ac("E3-S5-AC3")
@pytest.mark.parametrize("current", ["BOOKED", "CHECKED_IN"])
def test_no_show_only_after_start_and_slot_stays_booked(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers,
    current: str,
) -> None:
    appt, slot = _booked(client, engine, doctor, patient, timedelta(minutes=30))
    set_status(engine, appt, current)
    assert _status(client, doctor[1], appt, "NO_SHOW").status_code == 409
    assert len(events(engine, appt)) == 1
    set_slot_start(engine, slot, NOW + timedelta(seconds=1))
    assert _status(client, doctor[1], appt, "NO_SHOW").status_code == 409
    set_slot_start(engine, slot, NOW)  # now >= start_time is allowed
    response = _status(client, doctor[1], appt, "NO_SHOW")
    assert response.status_code == 200
    assert response.json()["status"] == "NO_SHOW"
    assert slot_status(engine, slot) == "BOOKED"
    assert events(engine, appt)[-1].event_type == "NO_SHOW"


@pytest.mark.ac("E3-S5-AC2")
def test_cancel_via_status_blocks_slot_and_refunds_once(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, payment: SpyPayment
) -> None:
    appt, slot = _booked(client, engine, doctor, patient)
    response = _status(client, doctor[1], appt, "CANCELLED")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert slot_status(engine, slot) == "BLOCKED"
    log = events(engine, appt)
    assert [(e.event_type, e.actor_role) for e in log[1:]] == [("CANCELLED", "DOCTOR")]
    assert [c[0] for c in payment.calls] == ["charge", "refund"]


@pytest.mark.ac("E3-S5-AC6")
def test_ownership_and_roles(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    appt, _ = _booked(client, engine, doctor, patient)
    _, other_doctor = onboard(client, admin, "d2@example.test")
    assert _status(client, other_doctor, appt, "CHECKED_IN").status_code == 404
    assert _status(client, other_doctor, appt, "CANCELLED").status_code == 404
    assert _status(client, doctor[1], 99999, "CHECKED_IN").status_code == 404
    assert _status(client, patient, appt, "CHECKED_IN").status_code == 403
    assert _status(client, admin, appt, "CHECKED_IN").status_code == 403
    assert _status(client, None, appt, "CHECKED_IN").status_code == 401
    assert appt_row(engine, appt).status == "BOOKED"
    assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S5-AC5")
def test_get_allowed_actions_per_role_and_clock(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers,
) -> None:
    appt, slot = _booked(client, engine, doctor, patient, timedelta(hours=3))

    def view(headers: Headers) -> dict[str, object]:
        response = client.get(f"/api/appointments/{appt}", headers=headers)
        assert response.status_code == 200
        body: dict[str, object] = response.json()
        return body

    assert view(doctor[1])["allowed_actions"] == ["CHECKED_IN", "CANCEL"]
    assert view(patient)["allowed_actions"] == ["CANCEL", "RESCHEDULE"]
    assert view(patient)["join_url"] is not None
    assert view(admin)["allowed_actions"] == []
    assert view(admin)["join_url"] is None
    set_slot_start(engine, slot, NOW)
    assert view(doctor[1])["allowed_actions"] == ["CHECKED_IN", "CANCEL", "NO_SHOW"]
    assert view(patient)["allowed_actions"] == []
    for state in ["COMPLETED", "CANCELLED", "NO_SHOW"]:
        set_status(engine, appt, state)
        assert view(doctor[1])["allowed_actions"] == []
        assert view(doctor[1])["join_url"] is None


@pytest.mark.ac("E3-S5-AC6")
def test_get_appointment_scoping(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    appt, _ = _booked(client, engine, doctor, patient)
    other_patient = register(client, "q@example.test")
    _, other_doctor = onboard(client, admin, "d2@example.test")
    get = client.get
    assert get(f"/api/appointments/{appt}", headers=other_patient).status_code == 404
    assert get(f"/api/appointments/{appt}", headers=other_doctor).status_code == 404
    assert get("/api/appointments/99999", headers=admin).status_code == 404
    assert get(f"/api/appointments/{appt}").status_code == 401
