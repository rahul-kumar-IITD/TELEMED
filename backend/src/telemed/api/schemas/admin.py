"""Request/response models for POST /api/admin/doctors (API-16). Never echoes the password."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from telemed.api.schemas.auth import Email, FullName
from telemed.api.schemas.doctors import (
    AvailabilityTemplateIn,
    AvailabilityTemplateOut,
    is_language_code,
)
from telemed.types.domain import DoctorOnboarding, OnboardedDoctor
from telemed.types.money import format_fee

Specialty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class OnboardDoctorRequest(BaseModel):
    email: Email
    initial_password: str = Field(min_length=8, max_length=128)
    full_name: FullName | None = None
    specialty: Specialty
    languages: list[str] = Field(min_length=1, max_length=10)
    fee: str  # a JSON string only; parsed and range-checked in the service layer
    availability_templates: list[AvailabilityTemplateIn] = Field(min_length=1, max_length=14)

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()

    @field_validator("languages")
    @classmethod
    def _languages(cls, value: list[str]) -> list[str]:
        codes = list(dict.fromkeys(code.strip().lower() for code in value))
        if not all(is_language_code(code) for code in codes):
            raise ValueError("each language must be 2 to 8 letters or hyphens")
        return codes

    def details(self) -> DoctorOnboarding:
        return DoctorOnboarding(
            email=self.email,
            full_name=self.full_name or self.email.split("@")[0][:200],
            specialty=self.specialty,
            languages=tuple(self.languages),
            fee=self.fee,
            templates=tuple(t.to_domain() for t in self.availability_templates),
        )


class OnboardDoctorResponse(BaseModel):
    doctor_id: int
    user_id: int
    email: str
    full_name: str
    specialty: str
    languages: list[str]
    fee: str
    availability_templates: list[AvailabilityTemplateOut]
    slots_created: int

    @classmethod
    def from_domain(cls, doctor: OnboardedDoctor) -> "OnboardDoctorResponse":
        return cls(
            doctor_id=doctor.doctor_id, user_id=doctor.doctor_id, email=doctor.email,
            full_name=doctor.full_name, specialty=doctor.specialty,
            languages=list(doctor.languages), fee=format_fee(doctor.fee),
            availability_templates=[
                AvailabilityTemplateOut.from_domain(t) for t in doctor.templates
            ],
            slots_created=doctor.slots_created,
        )
