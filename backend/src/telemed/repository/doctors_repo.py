"""doctor_profiles / availability_templates reads."""
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from telemed.repository.models import AvailabilityTemplate, DoctorProfile, User
from telemed.types.domain import StoredTemplate, TemplateSpec
from telemed.types.ids import UserId
from telemed.types.money import to_minor


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


def insert_doctor_profile(
    session: Session,
    doctor_id: UserId,
    full_name: str,
    specialty: str,
    languages: tuple[str, ...],
    fee: Decimal,
    now: datetime,
) -> None:
    session.add(
        DoctorProfile(
            doctor_id=doctor_id, full_name=full_name, specialty=specialty,
            languages=json.dumps(list(languages)), fee_minor=to_minor(fee),
            created_at=now, updated_at=now,
        )
    )
    session.flush()


def insert_template(
    session: Session, doctor_id: UserId, spec: TemplateSpec, now: datetime
) -> StoredTemplate:
    row = AvailabilityTemplate(
        doctor_id=doctor_id, weekday=spec.weekday, start_time=spec.start_time,
        end_time=spec.end_time, slot_length_minutes=spec.slot_length_minutes, created_at=now,
    )
    session.add(row)
    session.flush()
    return StoredTemplate(template_id=row.template_id, spec=spec)


def list_doctor_templates(session: Session, doctor_id: UserId) -> list[TemplateRow]:
    """All templates of one doctor."""
    stmt = (
        select(AvailabilityTemplate)
        .where(AvailabilityTemplate.doctor_id == doctor_id)
        .order_by(AvailabilityTemplate.template_id)
    )
    return [
        TemplateRow(
            doctor_id=UserId(row.doctor_id), weekday=row.weekday, start_time=row.start_time,
            end_time=row.end_time, slot_length_minutes=row.slot_length_minutes,
        )
        for row in session.scalars(stmt)
    ]
