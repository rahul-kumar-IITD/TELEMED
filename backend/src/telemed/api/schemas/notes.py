"""Consultation note request/response models (API-27..29)."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from telemed.types import domain

MAX_NOTE_CHARS = 5000


class NoteRequest(BaseModel):
    text: str = Field(strict=True, min_length=1, max_length=MAX_NOTE_CHARS)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class NoteOut(BaseModel):
    note_id: int
    appointment_id: int
    author_id: int
    text: str
    created_at: datetime

    @classmethod
    def from_domain(cls, note: domain.ConsultationNote) -> "NoteOut":
        return cls(
            note_id=note.note_id, appointment_id=note.appointment_id, author_id=note.author_id,
            text=note.text, created_at=note.created_at,
        )


class NoteList(BaseModel):
    items: list[NoteOut]
    total: int

    @classmethod
    def from_domain(cls, notes: list[domain.ConsultationNote]) -> "NoteList":
        return cls(items=[NoteOut.from_domain(n) for n in notes], total=len(notes))
