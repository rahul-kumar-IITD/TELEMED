"""consultation_notes access: insert and read only (the table is append-only)."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from telemed.repository.mappers import note_to_domain
from telemed.repository.models import ConsultationNote
from telemed.types import domain
from telemed.types.ids import AppointmentId, UserId


def insert(
    session: Session, appointment_id: AppointmentId, author_id: UserId, text: str, now: datetime
) -> domain.ConsultationNote:
    row = ConsultationNote(
        appointment_id=appointment_id, author_id=author_id, text=text, created_at=now
    )
    session.add(row)
    session.flush()
    return note_to_domain(row)


def list_for_appointment(
    session: Session, appointment_id: AppointmentId
) -> list[domain.ConsultationNote]:
    """Notes in creation order (ascending note_id)."""
    rows = session.scalars(
        select(ConsultationNote)
        .where(ConsultationNote.appointment_id == appointment_id)
        .order_by(ConsultationNote.note_id)
    )
    return [note_to_domain(r) for r in rows]


def get(
    session: Session, appointment_id: AppointmentId, note_id: int
) -> domain.ConsultationNote | None:
    """The note, only if it belongs to `appointment_id`."""
    row = session.scalars(
        select(ConsultationNote).where(
            ConsultationNote.appointment_id == appointment_id,
            ConsultationNote.note_id == note_id,
        )
    ).first()
    return None if row is None else note_to_domain(row)
