"""Doctor-driven appointment lifecycle, the daily queue and role-scoped appointment reads."""
import dataclasses
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from telemed.config.clock import Clock
from telemed.repository import appointments_repo, events_repo
from telemed.service.appointment_views import build_view
from telemed.service.cancellation_service import CancellationService
from telemed.service.integrations.interfaces import PaymentService, VideoService
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain, state_machine
from telemed.types.enums import AppointmentStatus, Role
from telemed.types.errors import InvalidAppointmentStateException, NotFoundException
from telemed.types.ids import AppointmentId


def _visible(actor: domain.User, appointment: domain.Appointment) -> bool:
    if actor.role is Role.PATIENT:
        return appointment.patient_id == actor.user_id
    if actor.role is Role.DOCTOR:
        return appointment.doctor_id == actor.user_id
    return True


class LifecycleService:
    def __init__(
        self, uow: UnitOfWork, clock: Clock, cancellation: CancellationService,
        provider_timezone: str,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._cancellation = cancellation
        self._tz = ZoneInfo(provider_timezone)
        self._tz_name = provider_timezone

    def change_status(
        self, doctor: domain.User, appointment_id: AppointmentId, target: AppointmentStatus,
        payment: PaymentService, video: VideoService,
    ) -> domain.AppointmentView:
        """Apply one state-machine transition and append exactly one DOCTOR event."""
        if target is AppointmentStatus.CANCELLED:
            return self._cancellation.cancel(doctor, appointment_id, payment)
        now = self._clock.now()
        with self._uow.transaction() as session:
            found = appointments_repo.get_with_slot(session, appointment_id)
            if found is None or found[0].doctor_id != doctor.user_id:
                raise NotFoundException()
            appointment, start, end = found
            if not state_machine.is_valid_transition(appointment.status, target, now >= start):
                raise InvalidAppointmentStateException()
            # status was read inside this BEGIN IMMEDIATE transaction, so the update applies
            appointments_repo.transition(session, appointment_id, appointment.status, target, now)
            events_repo.insert_transition(
                session, appointment_id, appointment.status, target, doctor.user_id, Role.DOCTOR,
                now,
            )
            moved = dataclasses.replace(appointment, status=target, updated_at=now)
            return build_view(session, moved, start, end, doctor, now, video)

    def get(
        self, actor: domain.User, appointment_id: AppointmentId, video: VideoService
    ) -> domain.AppointmentView:
        now = self._clock.now()
        with self._uow.read() as session:
            found = appointments_repo.get_with_slot(session, appointment_id)
            if found is None or not _visible(actor, found[0]):
                raise NotFoundException()
            return build_view(session, found[0], found[1], found[2], actor, now, video)

    def list_mine(
        self, patient: domain.User, status: AppointmentStatus | None, video: VideoService
    ) -> tuple[domain.AppointmentView, ...]:
        """The patient's own appointments, ascending by start time."""
        now = self._clock.now()
        with self._uow.read() as session:
            rows = appointments_repo.list_for_patient(session, patient.user_id, status)
            return tuple(build_view(session, a, s, e, patient, now, video) for a, s, e in rows)

    def queue(
        self, doctor: domain.User, day: date | None, video: VideoService
    ) -> domain.DoctorQueue:
        """Caller's appointments whose start is in [00:00, 24:00) of `day` in the provider zone."""
        now = self._clock.now()
        the_day = day if day is not None else now.astimezone(self._tz).date()
        lo = datetime.combine(the_day, time.min, tzinfo=self._tz).astimezone(UTC)
        hi = datetime.combine(the_day + timedelta(days=1), time.min, tzinfo=self._tz)
        with self._uow.read() as session:
            rows = appointments_repo.list_for_doctor_between(
                session, doctor.user_id, lo, hi.astimezone(UTC)
            )
            items = tuple(build_view(session, a, s, e, doctor, now, video) for a, s, e in rows)
        return domain.DoctorQueue(date=the_day.isoformat(), timezone=self._tz_name, items=items)
