"""Request/response models for patient profiles (API-06/07/08)."""
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from telemed.api.schemas.auth import FullName, Phone
from telemed.types.domain import PatientProfileView, ProfileChanges
from telemed.types.enums import Gender

Age = Annotated[int, Field(strict=True, ge=1, le=130)]


class ProfileUpdateRequest(BaseModel):
    """Partial update: omitted fields carry forward; explicit null or an empty body is 422."""

    full_name: FullName | None = None
    age: Age | None = None
    gender: Gender | None = None
    phone: Phone | None = None

    @field_validator("full_name", "age", "gender", "phone", mode="after")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("must not be null")
        return value

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self

    def changes(self) -> ProfileChanges:
        return ProfileChanges(
            full_name=self.full_name, age=self.age, gender=self.gender, phone=self.phone
        )


class PatientProfileResponse(BaseModel):
    patient_id: int
    version_number: int
    full_name: str
    age: int
    gender: Gender
    phone: str
    updated_at: datetime

    @field_serializer("updated_at")
    def _utc_z(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_domain(cls, view: PatientProfileView) -> "PatientProfileResponse":
        return cls(
            patient_id=view.patient_id, version_number=view.version_number,
            full_name=view.data.full_name, age=view.data.age, gender=view.data.gender,
            phone=view.data.phone, updated_at=view.updated_at,
        )
