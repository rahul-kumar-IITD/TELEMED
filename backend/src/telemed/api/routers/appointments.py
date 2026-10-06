"""Appointment endpoints."""
from fastapi import APIRouter, Depends

from telemed.api.deps import (
    get_booking_service,
    get_cancellation_service,
    get_current_user,
    get_lifecycle_service,
    get_payment_service,
    get_reschedule_service,
    get_video_service,
    require_roles,
)
from telemed.api.schemas.appointments import (
    AppointmentOut,
    BookRequest,
    RescheduleRequest,
    StatusRequest,
)
from telemed.service.booking_service import BookingService
from telemed.service.cancellation_service import CancellationService
from telemed.service.integrations.interfaces import PaymentService, VideoService
from telemed.service.lifecycle_service import LifecycleService
from telemed.service.reschedule_service import RescheduleService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import AppointmentId, SlotId

router = APIRouter(prefix="/api/appointments")

_patient_only = require_roles(Role.PATIENT)
_doctor_only = require_roles(Role.DOCTOR)
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


@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: int,
    user: domain.User = Depends(get_current_user),
    service: LifecycleService = Depends(get_lifecycle_service),
    video: VideoService = Depends(get_video_service),
) -> AppointmentOut:
    return AppointmentOut.from_domain(service.get(user, AppointmentId(appointment_id), video))


@router.post("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int,
    body: RescheduleRequest,
    user: domain.User = Depends(_patient_only),
    service: RescheduleService = Depends(get_reschedule_service),
    video: VideoService = Depends(get_video_service),
) -> AppointmentOut:
    view = service.reschedule(user, AppointmentId(appointment_id), SlotId(body.new_slot_id), video)
    return AppointmentOut.from_domain(view)


@router.post("/{appointment_id}/status")
def change_status(
    appointment_id: int,
    body: StatusRequest,
    user: domain.User = Depends(_doctor_only),
    service: LifecycleService = Depends(get_lifecycle_service),
    payment: PaymentService = Depends(get_payment_service),
    video: VideoService = Depends(get_video_service),
) -> AppointmentOut:
    view = service.change_status(user, AppointmentId(appointment_id), body.status, payment, video)
    return AppointmentOut.from_domain(view)
