"""doctor_profiles / availability_templates reads."""
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Row,
    ScalarSelect,
    Select,
    exists,
    func,
    literal_column,
    select,
)
from sqlalchemy.orm import Session

from telemed.repository.mappers import doctor_to_domain
from telemed.repository.models import AvailabilityTemplate, DoctorProfile, Slot, User
from telemed.types.domain import DoctorSearch, DoctorSummary, StoredTemplate, TemplateSpec
from telemed.types.enums import DoctorSort
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


def _earliest_open(now: datetime, horizon: datetime) -> ScalarSelect[datetime]:
    return (
        select(func.min(Slot.start_time))
        .where(
            Slot.doctor_id == DoctorProfile.doctor_id, Slot.status == "AVAILABLE",
            Slot.start_time > now, Slot.start_time < horizon,
        )
        .correlate(DoctorProfile)
        .scalar_subquery()
    )


def _summary_stmt(now: datetime, horizon: datetime) -> Select[Any, Any]:
    earliest = _earliest_open(now, horizon).label("earliest_slot")
    return (
        select(DoctorProfile, earliest)
        .join(User, User.user_id == DoctorProfile.doctor_id)
        .where(User.active == 1, User.role == "DOCTOR")
    )


def _to_summary(row: Row[Any, Any]) -> DoctorSummary:
    profile = doctor_to_domain(row[0])
    return DoctorSummary(
        doctor_id=profile.doctor_id, full_name=profile.full_name, specialty=profile.specialty,
        languages=profile.languages, fee=profile.fee, earliest_slot=row[1],
    )


def get_active_summary(
    session: Session, doctor_id: UserId, now: datetime, horizon: datetime
) -> DoctorSummary | None:
    """One active doctor's summary, or None if absent, deactivated or not a doctor."""
    row = session.execute(
        _summary_stmt(now, horizon).where(DoctorProfile.doctor_id == doctor_id)
    ).first()
    return None if row is None else _to_summary(row)


def search_active(
    session: Session, criteria: DoctorSearch, now: datetime, horizon: datetime
) -> list[DoctorSummary]:
    """Filtered, sorted summaries of active doctors (all filtering and ordering is in SQL)."""
    stmt = _summary_stmt(now, horizon)
    if criteria.specialty is not None:
        stmt = stmt.where(func.lower(DoctorProfile.specialty) == criteria.specialty.lower())
    if criteria.language is not None:
        languages = func.json_each(DoctorProfile.languages).table_valued("value")
        stmt = stmt.where(
            exists().where(func.lower(languages.c.value) == criteria.language.lower())
        )
    if criteria.available_from is not None or criteria.available_to is not None:
        open_slot = select(Slot.slot_id).where(
            Slot.doctor_id == DoctorProfile.doctor_id, Slot.status == "AVAILABLE"
        )
        if criteria.available_from is not None:
            open_slot = open_slot.where(Slot.start_time >= criteria.available_from)
        if criteria.available_to is not None:
            open_slot = open_slot.where(Slot.start_time <= criteria.available_to)
        stmt = stmt.where(open_slot.correlate(DoctorProfile).exists())
    earliest: ColumnElement[Any] = literal_column("earliest_slot")
    tie = (func.lower(DoctorProfile.full_name), DoctorProfile.doctor_id)
    if criteria.sort is DoctorSort.FEE:
        stmt = stmt.order_by(DoctorProfile.fee_minor, *tie)
    elif criteria.sort is DoctorSort.NAME:
        stmt = stmt.order_by(*tie)
    else:
        stmt = stmt.order_by(earliest.is_(None), earliest, *tie)
    return [_to_summary(row) for row in session.execute(stmt)]


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
