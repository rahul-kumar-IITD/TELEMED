"""doctor_profiles / availability_templates reads."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from telemed.repository.models import AvailabilityTemplate, User
from telemed.types.ids import UserId


@dataclass(frozen=True)
class TemplateRow:
    doctor_id: UserId
    weekday: int  # 0 = Monday
    start_time: str  # "HH:MM" provider-zone wall clock
    end_time: str
    slot_length_minutes: int


def list_active_doctor_templates(session: Session) -> list[TemplateRow]:
    """All templates belonging to active doctors."""
    stmt = (
        select(AvailabilityTemplate)
        .join(User, User.user_id == AvailabilityTemplate.doctor_id)
        .where(User.active == 1, User.role == "DOCTOR")
        .order_by(AvailabilityTemplate.template_id)
    )
    return [
        TemplateRow(
            doctor_id=UserId(row.doctor_id), weekday=row.weekday, start_time=row.start_time,
            end_time=row.end_time, slot_length_minutes=row.slot_length_minutes,
        )
        for row in session.scalars(stmt)
    ]
