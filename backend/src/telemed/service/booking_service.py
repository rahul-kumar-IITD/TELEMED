"""Atomic appointment booking."""
from datetime import timedelta

from telemed.config.clock import Clock
from telemed.repository import appointments_repo, doctors_repo, events_repo, slots_repo, users_repo
from telemed.service import allowed_actions
from telemed.service.integrations.interfaces import PaymentService, VideoService
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.errors import NotFoundException, SlotUnavailableException
from telemed.types.ids import SlotId

_BOOKING_WINDOW = timedelta(days=14)


class BookingService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def book(
        self, patient: domain.User, slot_id: SlotId, payment: PaymentService, video: VideoService
    ) -> domain.AppointmentView:
        """Claim slot + insert appointment and BOOKED event in one transaction, then charge."""
        now = self._clock.now()
        with self._uow.transaction() as session:
            if not slots_repo.claim(session, slot_id, now, now + _BOOKING_WINDOW):
                if slots_repo.get(session, slot_id) is None:
                    raise NotFoundException()
                raise SlotUnavailableException()
            slot = slots_repo.get(session, slot_id)
            assert slot is not None  # just claimed inside this transaction
            doctor = doctors_repo.get_profile(session, slot.doctor_id)
            assert doctor is not None  # slots.doctor_id is a foreign key to doctor_profiles
            appointment = appointments_repo.insert_booked(
                session, patient.user_id, slot.doctor_id, slot_id, doctor.fee, now
            )
            events_repo.insert_booked(session, appointment.appointment_id, patient.user_id, now)
            patient_name = users_repo.find_full_name(session, patient) or ""
        payment.charge(appointment.appointment_id, appointment.fee)
        return domain.AppointmentView(
            appointment=appointment, start_time=slot.start_time, end_time=slot.end_time,
            doctor_name=doctor.full_name, specialty=doctor.specialty, patient_name=patient_name,
            allowed_actions=allowed_actions.patient_booked_actions(slot.start_time, now),
            join_url=video.join_url(appointment.appointment_id),
            change_deadline=allowed_actions.change_deadline(slot.start_time),
        )
