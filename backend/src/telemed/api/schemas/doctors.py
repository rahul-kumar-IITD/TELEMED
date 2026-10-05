"""Availability template models shared by the doctor onboarding request and response."""
import re
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from telemed.types.domain import StoredTemplate, TemplateSpec

HHMM = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
_LANGUAGE = re.compile(r"^[a-z-]{2,8}$")


class AvailabilityTemplateIn(BaseModel):
    weekday: int = Field(strict=True, ge=0, le=6)
    start_time: HHMM
    end_time: HHMM
    slot_length_minutes: int = Field(strict=True)

    def to_domain(self) -> TemplateSpec:
        return TemplateSpec(
            weekday=self.weekday, start_time=self.start_time, end_time=self.end_time,
            slot_length_minutes=self.slot_length_minutes,
        )


class AvailabilityTemplateOut(AvailabilityTemplateIn):
    template_id: int

    @classmethod
    def from_domain(cls, stored: StoredTemplate) -> "AvailabilityTemplateOut":
        spec = stored.spec
        return cls(
            template_id=stored.template_id, weekday=spec.weekday, start_time=spec.start_time,
            end_time=spec.end_time, slot_length_minutes=spec.slot_length_minutes,
        )


def is_language_code(value: str) -> bool:
    return _LANGUAGE.fullmatch(value) is not None
