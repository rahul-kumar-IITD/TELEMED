"""Server-computed actions for an appointment, per caller role and the current clock."""
from datetime import datetime, timedelta

from telemed.types import state_machine
from telemed.types.enums import AppointmentStatus, Role

CHANGE_WINDOW = timedelta(minutes=60)


def change_deadline(start_time: datetime) -> datetime:
    """Last instant a patient may cancel or reschedule (inclusive)."""
    return start_time - CHANGE_WINDOW


def patient_booked_actions(start_time: datetime, now: datetime) -> tuple[str, ...]:
    """CANCEL and RESCHEDULE while at least 60 minutes remain, otherwise none."""
    if now <= change_deadline(start_time):
        return ("CANCEL", "RESCHEDULE")
    return ()


def actions_for(
    role: Role, status: AppointmentStatus, start_time: datetime, now: datetime
) -> tuple[str, ...]:
    """Allowed actions of an appointment's owner in `role`; ADMIN is read-only."""
    if role is Role.PATIENT:
        return patient_booked_actions(start_time, now) if status is AppointmentStatus.BOOKED else ()
    if role is Role.DOCTOR:
        nxt = state_machine.next_statuses(status, now >= start_time)
        return tuple("CANCEL" if s is AppointmentStatus.CANCELLED else s.value for s in nxt)
    return ()
