"""Append-only consultation notes. Note text is never logged."""
from sqlalchemy.orm import Session

from telemed.config.clock import Clock
from telemed.repository import appointments_repo, notes_repo
from telemed.service import bootstrap
from telemed.service.access import ensure_can_read
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.enums import AppointmentStatus
from telemed.types.errors import InvalidAppointmentStateException, NotFoundException
from telemed.types.ids import AppointmentId


def _ensure_visible(session: Session, actor: domain.User, appointment_id: AppointmentId) -> None:
    found = appointments_repo.get_with_slot(session, appointment_id)
    owners = None if found is None else {found[0].patient_id, found[0].doctor_id}
    ensure_can_read(actor, owners)


class NotesService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def add(
        self, doctor: domain.User, appointment_id: AppointmentId, text: str
    ) -> domain.ConsultationNote:
        """Append a note; only the appointment's own doctor, only once COMPLETED."""
        now = self._clock.now()
        with self._uow.transaction() as session:
            found = appointments_repo.get_with_slot(session, appointment_id)
            if found is None or found[0].doctor_id != doctor.user_id:
                raise NotFoundException()
            if found[0].status is not AppointmentStatus.COMPLETED:
                raise InvalidAppointmentStateException()
            note = notes_repo.insert(session, appointment_id, doctor.user_id, text, now)
        bootstrap.log_event("note_added", appointment_id=appointment_id, user_id=doctor.user_id)
        return note

    def list_notes(
        self, actor: domain.User, appointment_id: AppointmentId
    ) -> list[domain.ConsultationNote]:
        with self._uow.read() as session:
            _ensure_visible(session, actor, appointment_id)
            return notes_repo.list_for_appointment(session, appointment_id)

    def get(
        self, actor: domain.User, appointment_id: AppointmentId, note_id: int
    ) -> domain.ConsultationNote:
        with self._uow.read() as session:
            _ensure_visible(session, actor, appointment_id)
            note = notes_repo.get(session, appointment_id, note_id)
        if note is None:
            raise NotFoundException()
        return note
