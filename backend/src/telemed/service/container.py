"""Object graph for one running app: engine, clock and services, built from a Runtime."""
from dataclasses import dataclass

from telemed.config.clock import Clock, SystemClock
from telemed.repository.database import create_db_engine
from telemed.service.auth_service import AuthService
from telemed.service.booking_service import BookingService
from telemed.service.bootstrap import Runtime
from telemed.service.doctor_service import DoctorService
from telemed.service.integrations.interfaces import (
    NotificationService,
    PaymentService,
    PrescriptionService,
    VideoService,
)
from telemed.service.integrations.stubs import (
    StubNotificationService,
    StubPaymentService,
    StubPrescriptionService,
    StubVideoService,
)
from telemed.service.profile_service import ProfileService
from telemed.service.slot_generator import SlotGenerator
from telemed.service.unit_of_work import UnitOfWork

__all__ = ["Clock", "Container", "build_container"]


@dataclass(frozen=True)
class Container:
    runtime: Runtime
    clock: Clock
    uow: UnitOfWork
    auth: AuthService
    profiles: ProfileService
    doctors: DoctorService
    booking: BookingService
    slot_generator: SlotGenerator
    video: VideoService
    payment: PaymentService
    prescription: PrescriptionService
    notification: NotificationService


def build_container(runtime: Runtime, clock: Clock | None = None) -> Container:
    """Wire services with the default stub integrations. The engine connects lazily."""
    the_clock = clock if clock is not None else SystemClock()
    uow = UnitOfWork(create_db_engine(runtime.database_path, runtime.busy_timeout_ms))
    slot_generator = SlotGenerator(uow, the_clock, runtime.provider_timezone)
    return Container(
        runtime=runtime,
        clock=the_clock,
        uow=uow,
        auth=AuthService(uow, the_clock, runtime.jwt_secret, runtime.jwt_lifetime_minutes),
        profiles=ProfileService(uow, the_clock),
        doctors=DoctorService(uow, the_clock, slot_generator),
        booking=BookingService(uow, the_clock),
        slot_generator=slot_generator,
        video=StubVideoService(runtime.video_base_url),
        payment=StubPaymentService(),
        prescription=StubPrescriptionService(),
        notification=StubNotificationService(),
    )
