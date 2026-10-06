"""Appointment endpoints."""
from fastapi import APIRouter, Depends

from telemed.api.deps import (
    get_booking_service,
    get_cancellation_service,
    get_payment_service,
    get_video_service,
    require_roles,
)
from telemed.api.schemas.appointments import AppointmentOut, BookRequest
from telemed.service.booking_service import BookingService
from telemed.service.cancellation_service import CancellationService
from telemed.service.integrations.interfaces import PaymentService, VideoService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import AppointmentId, SlotId

router = APIRouter(prefix="/api/appointments")

_patient_only = require_roles(Role.PATIENT)
_patient_or_doctor = require_roles(Role.PATIENT, Role.DOCTOR)


@router.post("", status_code=201)
def book_appointment(
    body: BookRequest,
    user: domain.User = Depends(_patient_only),
    service: BookingService = Depends(get_booking_service),
    payment: PaymentService = Depends(get_payment_service),
    video: VideoService = Depends(get_video_service),
) -> AppointmentOut:
    return AppointmentOut.from_domain(service.book(user, SlotId(body.slot_id), payment, video))


@router.post("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    user: domain.User = Depends(_patient_or_doctor),
    service: CancellationService = Depends(get_cancellation_service),
    payment: PaymentService = Depends(get_payment_service),
) -> AppointmentOut:
    view = service.cancel(user, AppointmentId(appointment_id), payment)
    return AppointmentOut.from_domain(view)
