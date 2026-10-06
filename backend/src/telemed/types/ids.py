"""Typed integer identifiers."""
from typing import NewType

UserId = NewType("UserId", int)
SlotId = NewType("SlotId", int)
AppointmentId = NewType("AppointmentId", int)
NoteId = NewType("NoteId", int)
EventId = NewType("EventId", int)
TemplateId = NewType("TemplateId", int)
VersionId = NewType("VersionId", int)
