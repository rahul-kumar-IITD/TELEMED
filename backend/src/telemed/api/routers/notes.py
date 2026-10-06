"""Consultation note endpoints. PUT/PATCH/DELETE are unrouted, so Starlette answers 405 + Allow."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_current_user, get_notes_service, require_roles
from telemed.api.schemas.notes import NoteList, NoteOut, NoteRequest
from telemed.service.notes_service import NotesService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import AppointmentId

router = APIRouter(prefix="/api/appointments")

_doctor_only = require_roles(Role.DOCTOR)


@router.post("/{appointment_id}/notes", status_code=201)
def add_note(
    appointment_id: int,
    body: NoteRequest,
    user: domain.User = Depends(_doctor_only),
    service: NotesService = Depends(get_notes_service),
) -> NoteOut:
    return NoteOut.from_domain(service.add(user, AppointmentId(appointment_id), body.text))


@router.get("/{appointment_id}/notes")
def list_notes(
    appointment_id: int,
    user: domain.User = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service),
) -> NoteList:
    return NoteList.from_domain(service.list_notes(user, AppointmentId(appointment_id)))


@router.get("/{appointment_id}/notes/{note_id}")
def get_note(
    appointment_id: int,
    note_id: int,
    user: domain.User = Depends(get_current_user),
    service: NotesService = Depends(get_notes_service),
) -> NoteOut:
    return NoteOut.from_domain(service.get(user, AppointmentId(appointment_id), note_id))
