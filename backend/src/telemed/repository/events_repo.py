"""appointment_events (append-only) writes."""
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.repository.models import AppointmentEvent
from telemed.types.enums import AppointmentStatus, EventType, Role
from telemed.types.ids import AppointmentId, UserId


def insert_booked(
    session: Session, appointment_id: AppointmentId, actor_id: UserId, now: datetime
) -> None:
    session.add(
        AppointmentEvent(
            appointment_id=appointment_id, event_type=EventType.BOOKED.value, from_status=None,
            to_status=AppointmentStatus.BOOKED.value, actor_user_id=actor_id,
            actor_role=Role.PATIENT.value, created_at=now,
        )
    )
    session.flush()


def insert_cancelled(
    session: Session, appointment_id: AppointmentId, actor_id: UserId, actor_role: Role,
    now: datetime,
) -> None:
    session.add(
        AppointmentEvent(
            appointment_id=appointment_id, event_type=EventType.CANCELLED.value,
            from_status=AppointmentStatus.BOOKED.value,
            to_status=AppointmentStatus.CANCELLED.value, actor_user_id=actor_id,
            actor_role=actor_role.value, created_at=now,
        )
    )
    session.flush()
