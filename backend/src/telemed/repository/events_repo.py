"""appointment_events (append-only) writes."""
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.repository.models import AppointmentEvent
from telemed.types.enums import AppointmentStatus, EventType, Role
from telemed.types.ids import AppointmentId, SlotId, UserId


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


def insert_transition(
    session: Session, appointment_id: AppointmentId, from_status: AppointmentStatus,
    to_status: AppointmentStatus, actor_id: UserId, actor_role: Role, now: datetime,
) -> None:
    """One lifecycle event whose type equals the new status."""
    session.add(
        AppointmentEvent(
            appointment_id=appointment_id, event_type=EventType(to_status.value).value,
            from_status=from_status.value, to_status=to_status.value, actor_user_id=actor_id,
            actor_role=actor_role.value, created_at=now,
        )
    )
    session.flush()


def insert_rescheduled(
    session: Session, appointment_id: AppointmentId, old_slot_id: SlotId, new_slot_id: SlotId,
    actor_id: UserId, now: datetime,
) -> None:
    session.add(
        AppointmentEvent(
            appointment_id=appointment_id, event_type=EventType.RESCHEDULED.value,
            from_status=AppointmentStatus.BOOKED.value, to_status=AppointmentStatus.BOOKED.value,
            actor_user_id=actor_id, actor_role=Role.PATIENT.value, old_slot_id=old_slot_id,
            new_slot_id=new_slot_id, created_at=now,
        )
    )
    session.flush()
