"""Patient and doctor cancellation of BOOKED appointments."""
import dataclasses

from telemed.config.clock import Clock
from telemed.repository import (
    appointments_repo,
    doctors_repo,
    events_repo,
    profiles_repo,
    slots_repo,
)
from telemed.service import allowed_actions
from telemed.service.integrations.interfaces import PaymentService
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.enums import AppointmentStatus, Role, SlotStatus
from telemed.types.errors import (
    ChangeWindowClosedException,
    InvalidAppointmentStateException,
    NotFoundException,
)
from telemed.types.ids import AppointmentId


def _owns(actor: domain.User, appointment: domain.Appointment) -> bool:
    """Patient owns as patient, anyone else as doctor (the router admits PATIENT/DOCTOR only)."""
    if actor.role is Role.PATIENT:
        return appointment.patient_id == actor.user_id
    return appointment.doctor_id == actor.user_id


class CancellationService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def cancel(
        self, actor: domain.User, appointment_id: AppointmentId, payment: PaymentService
    ) -> domain.AppointmentView:
        """Cancel in one transaction (status, slot release, event), then refund once."""
        now = self._clock.now()
        with self._uow.transaction() as session:
            found = appointments_repo.get_with_slot(session, appointment_id)
            if found is None or not _owns(actor, found[0]):
                raise NotFoundException()
            appointment, start, end = found
            if appointment.status is not AppointmentStatus.BOOKED:
                raise InvalidAppointmentStateException()
            patient_cancel = actor.role is Role.PATIENT
            if patient_cancel and now > allowed_actions.change_deadline(start):
                raise ChangeWindowClosedException()
            released = SlotStatus.AVAILABLE if patient_cancel else SlotStatus.BLOCKED
            # status was read inside this BEGIN IMMEDIATE transaction, so both updates apply
            appointments_repo.transition(
                session, appointment_id, AppointmentStatus.BOOKED, AppointmentStatus.CANCELLED,
                now,
            )
            slots_repo.transition(
                session, appointment.slot_id, appointment.doctor_id, SlotStatus.BOOKED.value,
                released.value, now,
            )
            events_repo.insert_cancelled(session, appointment_id, actor.user_id, actor.role, now)
            doctor = doctors_repo.get_profile(session, appointment.doctor_id)
            assert doctor is not None  # appointments.doctor_id is a foreign key
            profile = profiles_repo.latest_version(session, appointment.patient_id)
            assert profile is not None  # every patient has a profile version
            patient_name = profile.data.full_name
        payment.refund(appointment_id, appointment.fee)
        return domain.AppointmentView(
            appointment=dataclasses.replace(
                appointment, status=AppointmentStatus.CANCELLED, updated_at=now
            ),
            start_time=start, end_time=end,
            doctor_name=doctor.full_name, specialty=doctor.specialty, patient_name=patient_name,
            allowed_actions=(), join_url=None,
            change_deadline=allowed_actions.change_deadline(start),
        )
