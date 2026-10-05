"""slots queries."""
from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from telemed.repository.models import Slot
from telemed.types.ids import UserId


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
