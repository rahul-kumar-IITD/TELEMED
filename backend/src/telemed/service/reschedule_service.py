"""Atomic patient reschedule of a BOOKED appointment to another slot of the same doctor."""
import dataclasses
from datetime import timedelta

from telemed.config.clock import Clock
from telemed.repository import appointments_repo, events_repo, slots_repo
from telemed.service import allowed_actions
from telemed.service.appointment_views import build_view
from telemed.service.integrations.interfaces import VideoService
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.enums import AppointmentStatus, SlotStatus
from telemed.types.errors import (
    ChangeWindowClosedException,
    InvalidAppointmentStateException,
    NotFoundException,
    SlotUnavailableException,
)
from telemed.types.ids import AppointmentId, SlotId

_BOOKING_WINDOW = timedelta(days=14)


class RescheduleService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def reschedule(
        self, patient: domain.User, appointment_id: AppointmentId, new_slot_id: SlotId,
        video: VideoService,
    ) -> domain.AppointmentView:
        """Claim target, release old slot, repoint appointment and log the event atomically."""
        now = self._clock.now()
        with self._uow.transaction() as session:
            found = appointments_repo.get_with_slot(session, appointment_id)
            if found is None or found[0].patient_id != patient.user_id:
                raise NotFoundException()
            appointment, start, _ = found
            if appointment.status is not AppointmentStatus.BOOKED:
                raise InvalidAppointmentStateException()
            if now > allowed_actions.change_deadline(start):
                raise ChangeWindowClosedException()
            target = slots_repo.get(session, new_slot_id)
            if target is None:
                raise NotFoundException()
            if not slots_repo.claim(
                session, new_slot_id, now, now + _BOOKING_WINDOW, appointment.doctor_id
            ):
                raise SlotUnavailableException()
            # state was read inside this BEGIN IMMEDIATE transaction, so the updates apply
            slots_repo.transition(
                session, appointment.slot_id, appointment.doctor_id, SlotStatus.BOOKED.value,
                SlotStatus.AVAILABLE.value, now,
            )
            appointments_repo.repoint_slot(
                session, appointment_id, appointment.slot_id, new_slot_id, now
            )
            events_repo.insert_rescheduled(
                session, appointment_id, appointment.slot_id, new_slot_id, patient.user_id, now
            )
            moved = dataclasses.replace(appointment, slot_id=new_slot_id, updated_at=now)
            return build_view(
                session, moved, target.start_time, target.end_time, patient, now, video
            )
