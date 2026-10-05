"""Frozen domain value types."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from telemed.types.enums import AppointmentStatus, Role, SlotStatus
from telemed.types.ids import AppointmentId, SlotId, UserId


@dataclass(frozen=True)
class User:
    user_id: UserId
    email: str
    role: Role
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DoctorProfile:
    doctor_id: UserId
    full_name: str
    specialty: str
    languages: tuple[str, ...]
    fee: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Slot:
    slot_id: SlotId
    doctor_id: UserId
    start_time: datetime
    end_time: datetime
    status: SlotStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Appointment:
    appointment_id: AppointmentId
    patient_id: UserId
    doctor_id: UserId
    slot_id: SlotId
    status: AppointmentStatus
    fee: Decimal
    created_at: datetime
    updated_at: datetime
