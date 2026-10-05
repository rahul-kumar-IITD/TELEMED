"""Row <-> domain mapping; the only place minor units become Decimal."""
import json

from telemed.repository.models import Appointment as AppointmentRow
from telemed.repository.models import DoctorProfile as DoctorProfileRow
from telemed.repository.models import Slot as SlotRow
from telemed.repository.models import User as UserRow
from telemed.types import domain
from telemed.types.enums import AppointmentStatus, Role, SlotStatus
from telemed.types.ids import AppointmentId, SlotId, UserId
from telemed.types.money import from_minor


def user_to_domain(row: UserRow) -> domain.User:
    return domain.User(
        user_id=UserId(row.user_id),
        email=row.email,
        role=Role(row.role),
        active=bool(row.active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def doctor_to_domain(row: DoctorProfileRow) -> domain.DoctorProfile:
    return domain.DoctorProfile(
        doctor_id=UserId(row.doctor_id),
        full_name=row.full_name,
        specialty=row.specialty,
        languages=tuple(json.loads(row.languages)),
        fee=from_minor(row.fee_minor),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def slot_to_domain(row: SlotRow) -> domain.Slot:
    return domain.Slot(
        slot_id=SlotId(row.slot_id),
        doctor_id=UserId(row.doctor_id),
        start_time=row.start_time,
        end_time=row.end_time,
        status=SlotStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def appointment_to_domain(row: AppointmentRow) -> domain.Appointment:
    return domain.Appointment(
        appointment_id=AppointmentId(row.appointment_id),
        patient_id=UserId(row.patient_id),
        doctor_id=UserId(row.doctor_id),
        slot_id=SlotId(row.slot_id),
        status=AppointmentStatus(row.status),
        fee=from_minor(row.fee_minor),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
