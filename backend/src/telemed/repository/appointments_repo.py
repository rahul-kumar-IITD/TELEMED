"""appointments queries."""
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from telemed.repository.mappers import appointment_to_domain
from telemed.repository.models import Appointment, Slot
from telemed.types import domain
from telemed.types.enums import AppointmentStatus
from telemed.types.ids import AppointmentId, SlotId, UserId
from telemed.types.money import to_minor


def insert_booked(
    session: Session, patient_id: UserId, doctor_id: UserId, slot_id: SlotId, fee: Decimal,
    now: datetime,
) -> domain.Appointment:
    """Insert a BOOKED appointment carrying the fee snapshot."""
    row = Appointment(
        patient_id=patient_id, doctor_id=doctor_id, slot_id=slot_id,
        status=AppointmentStatus.BOOKED.value, fee_minor=to_minor(fee),
        created_at=now, updated_at=now,
    )
    session.add(row)
    session.flush()
    return appointment_to_domain(row)


def get_with_slot(
    session: Session, appointment_id: AppointmentId
) -> tuple[domain.Appointment, datetime, datetime] | None:
    """The appointment with its current slot's (start, end), or None."""
    row = session.execute(
        select(Appointment, Slot.start_time, Slot.end_time)
        .join(Slot, Slot.slot_id == Appointment.slot_id)
        .where(Appointment.appointment_id == appointment_id)
    ).first()
    return None if row is None else (appointment_to_domain(row[0]), row[1], row[2])


def transition(
    session: Session, appointment_id: AppointmentId, expected: AppointmentStatus,
    new: AppointmentStatus, now: datetime,
) -> bool:
    """Single conditional UPDATE expected -> new; True if a row changed."""
    stmt = (
        update(Appointment)
        .where(Appointment.appointment_id == appointment_id, Appointment.status == expected.value)
        .values(status=new.value, updated_at=now)
    )
    return cast(CursorResult[Any], session.execute(stmt)).rowcount == 1


def count_open_for_doctor(session: Session, doctor_id: UserId) -> int:
    """Appointments of the doctor that are BOOKED, CHECKED_IN or IN_PROGRESS."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(("BOOKED", "CHECKED_IN", "IN_PROGRESS")),
            )
        )
        or 0
    )


def repoint_slot(
    session: Session, appointment_id: AppointmentId, old_slot_id: SlotId, new_slot_id: SlotId,
    now: datetime,
) -> bool:
    """Single conditional UPDATE moving a BOOKED appointment from old to new slot."""
    stmt = (
        update(Appointment)
        .where(
            Appointment.appointment_id == appointment_id, Appointment.slot_id == old_slot_id,
            Appointment.status == AppointmentStatus.BOOKED.value,
        )
        .values(slot_id=new_slot_id, updated_at=now)
    )
    return cast(CursorResult[Any], session.execute(stmt)).rowcount == 1


def list_for_doctor_between(
    session: Session, doctor_id: UserId, start: datetime, end: datetime
) -> list[tuple[domain.Appointment, datetime, datetime]]:
    """The doctor's appointments (all statuses) with slot start in [start, end), by start."""
    rows = session.execute(
        select(Appointment, Slot.start_time, Slot.end_time)
        .join(Slot, Slot.slot_id == Appointment.slot_id)
        .where(Appointment.doctor_id == doctor_id, Slot.start_time >= start, Slot.start_time < end)
        .order_by(Slot.start_time, Appointment.appointment_id)
    ).all()
    return [(appointment_to_domain(r[0]), r[1], r[2]) for r in rows]
