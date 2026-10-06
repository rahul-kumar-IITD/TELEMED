"""Appointment request/response models (API-21)."""
from datetime import datetime

from pydantic import BaseModel, Field

from telemed.types import domain
from telemed.types.money import format_fee


class BookRequest(BaseModel):
    slot_id: int = Field(strict=True)


class DoctorRef(BaseModel):
    doctor_id: int
    full_name: str
    specialty: str


class PatientRef(BaseModel):
    patient_id: int
    full_name: str


class AppointmentOut(BaseModel):
    appointment_id: int
    status: str
    slot_id: int
    start_time: datetime
    end_time: datetime
    doctor: DoctorRef
    patient: PatientRef
    fee: str
    allowed_actions: list[str]
    join_url: str | None
    change_deadline: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, view: domain.AppointmentView) -> "AppointmentOut":
        appt = view.appointment
        return cls(
            appointment_id=appt.appointment_id, status=appt.status.value, slot_id=appt.slot_id,
            start_time=view.start_time, end_time=view.end_time,
            doctor=DoctorRef(
                doctor_id=appt.doctor_id, full_name=view.doctor_name, specialty=view.specialty
            ),
            patient=PatientRef(patient_id=appt.patient_id, full_name=view.patient_name),
            fee=format_fee(appt.fee), allowed_actions=list(view.allowed_actions),
            join_url=view.join_url, change_deadline=view.change_deadline,
            created_at=appt.created_at, updated_at=appt.updated_at,
        )
