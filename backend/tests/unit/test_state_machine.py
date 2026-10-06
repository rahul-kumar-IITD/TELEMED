"""E3-S5: full transition matrix and allowed_actions of the appointment state machine."""
from datetime import UTC, datetime, timedelta
from itertools import product

import pytest

from telemed.service import allowed_actions
from telemed.types import state_machine
from telemed.types.enums import AppointmentStatus as S
from telemed.types.enums import Role

LEGAL = {
    (S.BOOKED, S.CHECKED_IN), (S.BOOKED, S.CANCELLED), (S.BOOKED, S.NO_SHOW),
    (S.CHECKED_IN, S.IN_PROGRESS), (S.CHECKED_IN, S.NO_SHOW), (S.IN_PROGRESS, S.COMPLETED),
}
START = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


@pytest.mark.ac("E3-S5-AC2")
@pytest.mark.parametrize(("current", "target"), list(product(S, S)))
def test_matrix_after_start(current: S, target: S) -> None:
    assert state_machine.is_valid_transition(current, target, True) == ((current, target) in LEGAL)


@pytest.mark.ac("E3-S5-AC3")
@pytest.mark.parametrize(("current", "target"), list(product(S, S)))
def test_matrix_before_start_refuses_no_show(current: S, target: S) -> None:
    expected = (current, target) in LEGAL and target is not S.NO_SHOW
    assert state_machine.is_valid_transition(current, target, False) == expected


@pytest.mark.ac("E3-S5-AC5")
@pytest.mark.parametrize(
    ("status", "before", "after"),
    [
        (S.BOOKED, ("CHECKED_IN", "CANCEL"), ("CHECKED_IN", "CANCEL", "NO_SHOW")),
        (S.CHECKED_IN, ("IN_PROGRESS",), ("IN_PROGRESS", "NO_SHOW")),
        (S.IN_PROGRESS, ("COMPLETED",), ("COMPLETED",)),
        (S.COMPLETED, (), ()),
        (S.CANCELLED, (), ()),
        (S.NO_SHOW, (), ()),
    ],
)
def test_doctor_actions(status: S, before: tuple[str, ...], after: tuple[str, ...]) -> None:
    assert allowed_actions.actions_for(Role.DOCTOR, status, START, START - timedelta(1)) == before
    assert allowed_actions.actions_for(Role.DOCTOR, status, START, START) == after


@pytest.mark.ac("E3-S5-AC5")
def test_patient_and_admin_actions() -> None:
    early = START - timedelta(hours=2)
    assert allowed_actions.actions_for(Role.PATIENT, S.BOOKED, START, early) == (
        "CANCEL", "RESCHEDULE")
    assert allowed_actions.actions_for(Role.PATIENT, S.BOOKED, START, START) == ()
    assert allowed_actions.actions_for(Role.PATIENT, S.CHECKED_IN, START, early) == ()
    assert allowed_actions.actions_for(Role.ADMIN, S.BOOKED, START, early) == ()
