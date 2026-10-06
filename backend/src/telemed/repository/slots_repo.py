"""slots queries."""
from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from telemed.repository.mappers import slot_to_domain
from telemed.repository.models import Slot
from telemed.types import domain
from telemed.types.ids import SlotId, UserId


def insert_available_if_absent(
    session: Session, doctor_id: UserId, start: datetime, end: datetime, now: datetime
) -> bool:
    """INSERT ... ON CONFLICT(doctor_id, start_time) DO NOTHING; True if a row was created."""
    stmt = (
        insert(Slot)
        .values(
            doctor_id=doctor_id, start_time=start, end_time=end, status="AVAILABLE",
            created_at=now, updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["doctor_id", "start_time"])
    )
    result = cast(CursorResult[Any], session.execute(stmt))
    return result.rowcount == 1


def _to_domain(rows: Iterable[Slot]) -> list[domain.Slot]:
    return [slot_to_domain(row) for row in rows]


def list_for_doctor(
    session: Session, doctor_id: UserId, start: datetime, end: datetime
) -> list[domain.Slot]:
    """All of one doctor's slots (any status) with start_time in [start, end], oldest first."""
    stmt = (
        select(Slot)
        .where(Slot.doctor_id == doctor_id, Slot.start_time >= start, Slot.start_time <= end)
        .order_by(Slot.start_time)
    )
    return _to_domain(session.scalars(stmt))


def list_open(
    session: Session, doctor_id: UserId, after: datetime, before: datetime
) -> list[domain.Slot]:
    """AVAILABLE slots with after < start_time < before, oldest first."""
    stmt = (
        select(Slot)
        .where(
            Slot.doctor_id == doctor_id, Slot.status == "AVAILABLE",
            Slot.start_time > after, Slot.start_time < before,
        )
        .order_by(Slot.start_time)
    )
    return _to_domain(session.scalars(stmt))


def transition(
    session: Session, slot_id: SlotId, doctor_id: UserId, expected: str, new: str, now: datetime
) -> bool:
    """Single conditional UPDATE expected -> new scoped to the owner; True if a row changed."""
    stmt = (
        update(Slot)
        .where(Slot.slot_id == slot_id, Slot.doctor_id == doctor_id, Slot.status == expected)
        .values(status=new, updated_at=now)
    )
    return cast(CursorResult[Any], session.execute(stmt)).rowcount == 1


def get_owned(session: Session, slot_id: SlotId, doctor_id: UserId) -> domain.Slot | None:
    """The slot if it exists and belongs to the doctor, else None."""
    row = session.scalars(
        select(Slot).where(Slot.slot_id == slot_id, Slot.doctor_id == doctor_id)
    ).first()
    return None if row is None else slot_to_domain(row)
