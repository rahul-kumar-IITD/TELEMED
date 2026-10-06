"""E3-S4: patient reschedule (API-25)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from telemed.repository import events_repo
from telemed.repository.models import Slot
from tests.integration.conftest import (
    NOW,
    Doctor,
    Headers,
    appt_row,
    book,
    book_at,
    events,
    onboard,
    register,
    set_slot_start,
    set_status,
    slot_ids,
    slot_status,
)


def _resched(
    client: TestClient, headers: Headers | None, appt: int, body: object
) -> Response:
    return client.post(f"/api/appointments/{appt}/reschedule", headers=headers or {}, json=body)


def _setup(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers,
    start_in: timedelta = timedelta(hours=5),
) -> tuple[int, int, int]:
    """(appointment, current slot, an open target slot)."""
    target = slot_ids(engine, doctor[0], 5)[-1]
    appt, current = book_at(client, engine, doctor[0], patient, NOW + start_in)
    return appt, current, target


@pytest.mark.ac("E3-S4-AC1")
@pytest.mark.ac("AC-07")
def test_reschedule_moves_slots_keeps_id(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, old, new = _setup(client, engine, doctor, patient)
    response = _resched(client, patient, appt, {"new_slot_id": new})
    assert response.status_code == 200
    body = response.json()
    assert body["appointment_id"] == appt
    assert body["slot_id"] == new
    assert body["status"] == "BOOKED"
    assert body["allowed_actions"] == ["CANCEL", "RESCHEDULE"]
    assert slot_status(engine, new) == "BOOKED"
    assert slot_status(engine, old) == "AVAILABLE"
    assert appt_row(engine, appt).slot_id == new
    fetched = client.get(f"/api/appointments/{appt}", headers=patient).json()
    assert fetched["start_time"] == body["start_time"]


@pytest.mark.ac("E3-S4-AC2")
def test_reschedule_appends_one_event_with_both_slots(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, old, new = _setup(client, engine, doctor, patient)
    _resched(client, patient, appt, {"new_slot_id": new})
    log = events(engine, appt)
    assert [e.event_type for e in log] == ["BOOKED", "RESCHEDULED"]
    assert (log[-1].old_slot_id, log[-1].new_slot_id) == (old, new)
    assert log[-1].actor_role == "PATIENT"


@pytest.mark.ac("E3-S4-AC3")
@pytest.mark.parametrize(
    "case", ["booked", "blocked", "started", "beyond_window", "same", "other_doctor"]
)
def test_invalid_targets_are_409_and_change_nothing(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers,
    case: str,
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient)
    if case == "booked":
        other = register(client, "q@example.test")
        book(client, other, target)
    elif case == "blocked":
        client.put(f"/api/doctors/me/slots/{target}/block", headers=doctor[1])
    elif case == "started":
        set_slot_start(engine, target, NOW - timedelta(minutes=5))
    elif case == "beyond_window":
        set_slot_start(engine, target, NOW + timedelta(days=15))
    elif case == "other_doctor":
        other_id, _ = onboard(client, admin, "d2@example.test")
        target = slot_ids(engine, other_id, 1)[0]
    new_id = current if case == "same" else target
    before = slot_status(engine, new_id)
    response = _resched(client, patient, appt, {"new_slot_id": new_id})
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_UNAVAILABLE"
    assert appt_row(engine, appt).slot_id == current
    assert slot_status(engine, current) == "BOOKED"
    assert slot_status(engine, new_id) == before or new_id == current
    assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S4-AC3")
def test_unknown_target_404_and_bad_body_422(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, _, _ = _setup(client, engine, doctor, patient)
    assert _resched(client, patient, appt, {"new_slot_id": 999999}).status_code == 404
    assert _resched(client, patient, appt, {}).status_code == 422
    assert _resched(client, patient, appt, {"new_slot_id": "x"}).status_code == 422


@pytest.mark.ac("E3-S4-AC3")
def test_inactive_doctor_target_is_409(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient)
    set_status(engine, appt, "CANCELLED")  # lets the doctor be deactivated
    client.put(f"/api/admin/users/{doctor[0]}/deactivate", headers=admin)
    set_status(engine, appt, "BOOKED")
    assert _resched(client, patient, appt, {"new_slot_id": target}).status_code == 409


@pytest.mark.ac("E3-S4-AC4")
@pytest.mark.parametrize(
    ("lead", "expected"),
    [
        (timedelta(minutes=60), 200),
        (timedelta(minutes=59, seconds=59), 409),
        (timedelta(minutes=-5), 409),
    ],
)
def test_sixty_minute_boundary(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, lead: timedelta,
    expected: int,
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient, lead)
    response = _resched(client, patient, appt, {"new_slot_id": target})
    assert response.status_code == expected
    if expected == 409:
        assert response.json()["code"] == "CHANGE_WINDOW_CLOSED"
        assert slot_status(engine, target) == "AVAILABLE"
        assert appt_row(engine, appt).slot_id == current
        assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S4-AC5")
@pytest.mark.parametrize(
    "state", ["CHECKED_IN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"]
)
def test_non_booked_states_are_409(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers, state: str
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient)
    set_status(engine, appt, state)
    response = _resched(client, patient, appt, {"new_slot_id": target})
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_APPOINTMENT_STATE"
    assert slot_status(engine, target) == "AVAILABLE"
    assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S4-AC6")
def test_failure_after_claim_rolls_everything_back(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected")

    monkeypatch.setattr(events_repo, "insert_rescheduled", boom)
    response = _resched(client, patient, appt, {"new_slot_id": target})
    assert response.status_code == 500
    assert slot_status(engine, target) == "AVAILABLE"
    assert slot_status(engine, current) == "BOOKED"
    assert appt_row(engine, appt).slot_id == current
    assert len(events(engine, appt)) == 1


@pytest.mark.ac("E3-S4-AC1")
def test_auth_rules(
    client: TestClient, engine: Engine, admin: Headers, doctor: Doctor, patient: Headers
) -> None:
    appt, current, target = _setup(client, engine, doctor, patient)
    body = {"new_slot_id": target}
    assert _resched(client, None, appt, body).status_code == 401
    assert _resched(client, doctor[1], appt, body).status_code == 403
    assert _resched(client, admin, appt, body).status_code == 403
    other = register(client, "q@example.test")
    assert _resched(client, other, appt, body).status_code == 404
    assert _resched(client, patient, 99999, body).status_code == 404
    assert slot_status(engine, target) == "AVAILABLE"
    assert appt_row(engine, appt).slot_id == current


def test_claim_excludes_target_that_became_unavailable(
    client: TestClient, engine: Engine, doctor: Doctor, patient: Headers
) -> None:
    appt, _, target = _setup(client, engine, doctor, patient)
    with Session(engine) as session:
        session.execute(update(Slot).where(Slot.slot_id == target).values(status="BLOCKED"))
        session.commit()
    assert _resched(client, patient, appt, {"new_slot_id": target}).status_code == 409
