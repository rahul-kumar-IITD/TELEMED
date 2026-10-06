"""Appointment endpoints."""
from fastapi import APIRouter, Depends

from telemed.api.deps import (
    get_booking_service,
    get_payment_service,
    get_video_service,
    require_roles,
)
from telemed.api.schemas.appointments import AppointmentOut, BookRequest
from telemed.service.booking_service import BookingService
from telemed.service.integrations.interfaces import PaymentService, VideoService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import SlotId

router = APIRouter(prefix="/api/appointments")

_patient_only = require_roles(Role.PATIENT)


@router.post("", status_code=201)
def book_appointment(
    body: BookRequest,
    user: domain.User = Depends(_patient_only),
    service: BookingService = Depends(get_booking_service),
    payment: PaymentService = Depends(get_payment_service),
    video: VideoService = Depends(get_video_service),
) -> AppointmentOut:
    return AppointmentOut.from_domain(service.book(user, SlotId(body.slot_id), payment, video))
