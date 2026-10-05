"""Frozen domain value types."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from telemed.types.enums import AppointmentStatus, Gender, Role, SlotStatus
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


@dataclass(frozen=True)
class ProfileData:
    """Patient contact/profile fields captured at registration (profile version content)."""

    full_name: str
    age: int
    gender: Gender
    phone: str


@dataclass(frozen=True)
class AccessToken:
    access_token: str
    token_type: str
    expires_in: int
    expires_at: datetime


@dataclass(frozen=True)
class LoginResult:
    token: AccessToken
    user_id: UserId
    role: Role


@dataclass(frozen=True)
class TokenClaims:
    user_id: UserId
    role: str
    expires_at: datetime


@dataclass(frozen=True)
class UserView:
    """A user plus the display name shown by GET /api/auth/me."""

    user: User
    full_name: str | None
