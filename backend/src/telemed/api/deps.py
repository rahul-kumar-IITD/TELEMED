"""FastAPI dependency providers. Every provider is overridable via `dependency_overrides`."""
from fastapi import Depends, Request

from telemed.service.auth_service import AuthService
from telemed.service.container import Container
from telemed.service.integrations.interfaces import (
    NotificationService,
    PaymentService,
    PrescriptionService,
    VideoService,
)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_auth_service(container: Container = Depends(get_container)) -> AuthService:
    return container.auth


def get_video_service(container: Container = Depends(get_container)) -> VideoService:
    return container.video


def get_payment_service(container: Container = Depends(get_container)) -> PaymentService:
    return container.payment


def get_prescription_service(
    container: Container = Depends(get_container),
) -> PrescriptionService:
    return container.prescription


def get_notification_service(
    container: Container = Depends(get_container),
) -> NotificationService:
    return container.notification
