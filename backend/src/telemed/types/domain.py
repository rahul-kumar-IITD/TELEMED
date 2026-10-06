"""Frozen domain value types."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from telemed.types.enums import AppointmentStatus, DoctorSort, Gender, Role, SlotStatus
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


@dataclass(frozen=True)
class PatientProfileView:
    """The latest (or a specific) profile version of a patient."""

    patient_id: UserId
    version_number: int
    data: ProfileData
    updated_at: datetime


@dataclass(frozen=True)
class ProfileChanges:
    """Partial profile update; None means "carry forward from the current version"."""

    full_name: str | None = None
    age: int | None = None
    gender: Gender | None = None
    phone: str | None = None


@dataclass(frozen=True)
class TemplateSpec:
    """One weekly availability window (wall clock in the provider timezone)."""

    weekday: int  # 0 = Monday
    start_time: str  # "HH:MM"
    end_time: str
    slot_length_minutes: int


@dataclass(frozen=True)
class StoredTemplate:
    template_id: int
    spec: TemplateSpec


@dataclass(frozen=True)
class DoctorOnboarding:
    """Admin input for creating a doctor; `fee` is the raw string, parsed by the service."""

    email: str
    full_name: str
    specialty: str
    languages: tuple[str, ...]
    fee: str
    templates: tuple[TemplateSpec, ...]


@dataclass(frozen=True)
class OnboardedDoctor:
    doctor_id: UserId
    email: str
    full_name: str
    specialty: str
    languages: tuple[str, ...]
    fee: Decimal
    templates: tuple[StoredTemplate, ...]
    slots_created: int


@dataclass(frozen=True)
class DoctorSummary:
    """A doctor as shown in search results; earliest_slot is the next open slot, if any."""

    doctor_id: UserId
    full_name: str
    specialty: str
    languages: tuple[str, ...]
    fee: Decimal
    earliest_slot: datetime | None


@dataclass(frozen=True)
class DoctorSearch:
    """Search filters and sort; datetimes are tz-aware and already validated."""

    specialty: str | None = None
    language: str | None = None
    available_from: datetime | None = None
    available_to: datetime | None = None
    sort: DoctorSort = DoctorSort.EARLIEST_SLOT
