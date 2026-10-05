"""SQLAlchemy 2 models. Money columns are integer minor units (`fee_minor`)."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from telemed.repository.types import UtcDateTime

_APPT_STATUSES = "'BOOKED','CHECKED_IN','IN_PROGRESS','COMPLETED','CANCELLED','NO_SHOW'"
_EVENT_TYPES = _APPT_STATUSES + ",'RESCHEDULED'"
_ROLES = "'PATIENT','DOCTOR','ADMIN'"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_lower"),
        CheckConstraint("password_hash LIKE '$argon2%'", name="ck_users_password_hash"),
        CheckConstraint(f"role IN ({_ROLES})", name="ck_users_role"),
        CheckConstraint("active IN (0,1)", name="ck_users_active"),
        Index("ix_users_role_active", "role", "active"),
    )
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class PatientProfileVersion(Base):
    __tablename__ = "patient_profile_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="ck_ppv_version"),
        CheckConstraint("length(trim(full_name)) >= 1", name="ck_ppv_full_name"),
        CheckConstraint("age > 0 AND age <= 130", name="ck_ppv_age"),
        CheckConstraint(
            "gender IN ('FEMALE','MALE','OTHER','UNDISCLOSED')", name="ck_ppv_gender"
        ),
        CheckConstraint("length(trim(phone)) >= 1", name="ck_ppv_phone"),
        Index("uq_ppv_patient_version", "patient_id", "version_number", unique=True),
    )
    version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.patient_id"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        CheckConstraint("length(specialty) >= 1", name="ck_doctor_specialty"),
        CheckConstraint(
            "json_valid(languages) AND json_array_length(languages) BETWEEN 1 AND 10",
            name="ck_doctor_languages",
        ),
        CheckConstraint("fee_minor >= 0", name="ck_doctor_fee"),
        Index("ix_doctor_specialty", text("lower(specialty)")),
    )
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    languages: Mapped[str] = mapped_column(Text, nullable=False)
    fee_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class AvailabilityTemplate(Base):
    __tablename__ = "availability_templates"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_tpl_weekday"),
        CheckConstraint("end_time > start_time", name="ck_tpl_window"),
        CheckConstraint("slot_length_minutes > 0", name="ck_tpl_length"),
        Index("ix_templates_doctor_weekday", "doctor_id", "weekday"),
    )
    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.doctor_id"))
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    slot_length_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_slots_window"),
        CheckConstraint("status IN ('AVAILABLE','BOOKED','BLOCKED')", name="ck_slots_status"),
        Index("uq_slots_doctor_start", "doctor_id", "start_time", unique=True),
        Index("ix_slots_doctor_status_start", "doctor_id", "status", "start_time"),
        Index("ix_slots_status_start", "status", "start_time"),
    )
    slot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.doctor_id"))
    start_time: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="AVAILABLE")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(f"status IN ({_APPT_STATUSES})", name="ck_appt_status"),
        CheckConstraint("fee_minor >= 0", name="ck_appt_fee"),
        Index(
            "uq_appt_slot_live",
            "slot_id",
            unique=True,
            sqlite_where=text("status <> 'CANCELLED'"),
        ),
        Index("ix_appt_patient_status", "patient_id", "status"),
        Index("ix_appt_doctor_status", "doctor_id", "status"),
        Index("ix_appt_slot", "slot_id"),
    )
    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.patient_id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.doctor_id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.slot_id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="BOOKED")
    fee_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class AppointmentEvent(Base):
    __tablename__ = "appointment_events"
    __table_args__ = (
        CheckConstraint(f"event_type IN ({_EVENT_TYPES})", name="ck_ae_event_type"),
        CheckConstraint(
            f"from_status IS NULL OR from_status IN ({_APPT_STATUSES})", name="ck_ae_from"
        ),
        CheckConstraint(f"to_status IN ({_APPT_STATUSES})", name="ck_ae_to"),
        CheckConstraint(f"actor_role IN ({_ROLES})", name="ck_ae_actor_role"),
        CheckConstraint(
            "(event_type = 'RESCHEDULED') = "
            "(old_slot_id IS NOT NULL AND new_slot_id IS NOT NULL)",
            name="ck_ae_reschedule_slots",
        ),
        Index("ix_events_appt", "appointment_id", "event_id"),
    )
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.appointment_id"))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    from_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    actor_role: Mapped[str] = mapped_column(Text, nullable=False)
    old_slot_id: Mapped[int | None] = mapped_column(ForeignKey("slots.slot_id"), nullable=True)
    new_slot_id: Mapped[int | None] = mapped_column(ForeignKey("slots.slot_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"
    __table_args__ = (
        CheckConstraint("length(trim(text)) >= 1 AND length(text) <= 5000", name="ck_cn_text"),
        Index("ix_notes_appt", "appointment_id", "note_id"),
    )
    note_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.appointment_id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.doctor_id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
