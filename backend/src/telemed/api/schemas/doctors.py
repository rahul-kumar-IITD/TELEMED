"""Availability template models shared by the doctor onboarding request and response."""
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from telemed.types.domain import DoctorSummary, StoredTemplate, TemplateSpec
from telemed.types.money import format_fee

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


class DoctorSummaryOut(BaseModel):
    doctor_id: int
    full_name: str
    specialty: str
    languages: list[str]
    fee: str
    earliest_slot: datetime | None

    @classmethod
    def from_domain(cls, doctor: DoctorSummary) -> "DoctorSummaryOut":
        return cls(
            doctor_id=doctor.doctor_id, full_name=doctor.full_name, specialty=doctor.specialty,
            languages=list(doctor.languages), fee=format_fee(doctor.fee),
            earliest_slot=doctor.earliest_slot,
        )


class DoctorListResponse(BaseModel):
    items: list[DoctorSummaryOut]
    total: int

    @classmethod
    def from_domain(cls, doctors: list[DoctorSummary]) -> "DoctorListResponse":
        items = [DoctorSummaryOut.from_domain(doctor) for doctor in doctors]
        return cls(items=items, total=len(items))


def is_language_code(value: str) -> bool:
    return _LANGUAGE.fullmatch(value) is not None
