"""Server-computed actions for an appointment (initial: the patient's BOOKED view)."""
from datetime import datetime, timedelta

CHANGE_WINDOW = timedelta(minutes=60)


def change_deadline(start_time: datetime) -> datetime:
    """Last instant a patient may cancel or reschedule (inclusive)."""
    return start_time - CHANGE_WINDOW


def patient_booked_actions(start_time: datetime, now: datetime) -> tuple[str, ...]:
    """CANCEL and RESCHEDULE while at least 60 minutes remain, otherwise none."""
    if now <= change_deadline(start_time):
        return ("CANCEL", "RESCHEDULE")
    return ()
