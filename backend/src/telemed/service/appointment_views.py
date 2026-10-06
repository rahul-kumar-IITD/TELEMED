"""Builds the caller-specific AppointmentView inside an open session."""
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.repository import doctors_repo, profiles_repo
from telemed.service import allowed_actions
from telemed.service.integrations.interfaces import VideoService
from telemed.types import domain
from telemed.types.enums import AppointmentStatus, Role

_LIVE = (AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_PROGRESS)


def build_view(
    session: Session, appointment: domain.Appointment, start: datetime, end: datetime,
    actor: domain.User, now: datetime, video: VideoService,
) -> domain.AppointmentView:
    doctor = doctors_repo.get_profile(session, appointment.doctor_id)
    assert doctor is not None  # appointments.doctor_id is a foreign key
    profile = profiles_repo.latest_version(session, appointment.patient_id)
    assert profile is not None  # every patient has a profile version
    live = actor.role is not Role.ADMIN and appointment.status in _LIVE
    return domain.AppointmentView(
        appointment=appointment, start_time=start, end_time=end,
        doctor_name=doctor.full_name, specialty=doctor.specialty,
        patient_name=profile.data.full_name,
        allowed_actions=allowed_actions.actions_for(actor.role, appointment.status, start, now),
        join_url=video.join_url(appointment.appointment_id) if live else None,
        change_deadline=allowed_actions.change_deadline(start),
    )
