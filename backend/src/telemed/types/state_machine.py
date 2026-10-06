"""Appointment state machine: the single source of truth for legal status transitions."""
from telemed.types.enums import AppointmentStatus as S

# Order matters: it is the order of the doctor's allowed_actions.
TRANSITIONS: dict[S, tuple[S, ...]] = {
    S.BOOKED: (S.CHECKED_IN, S.CANCELLED, S.NO_SHOW),
    S.CHECKED_IN: (S.IN_PROGRESS, S.NO_SHOW),
    S.IN_PROGRESS: (S.COMPLETED,),
    S.COMPLETED: (),
    S.CANCELLED: (),
    S.NO_SHOW: (),
}


def next_statuses(current: S, started: bool) -> tuple[S, ...]:
    """Statuses reachable from `current`; NO_SHOW only once the appointment has started."""
    return tuple(s for s in TRANSITIONS[current] if s is not S.NO_SHOW or started)


def is_valid_transition(current: S, target: S, started: bool) -> bool:
    return target in next_statuses(current, started)
