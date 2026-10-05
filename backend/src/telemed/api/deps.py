"""FastAPI dependency providers. Every provider is overridable via `dependency_overrides`."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from telemed.service.auth_service import AuthService
from telemed.service.container import Container
from telemed.service.doctor_service import DoctorService
from telemed.service.integrations.interfaces import (
    NotificationService,
    PaymentService,
    PrescriptionService,
    VideoService,
)
from telemed.service.profile_service import ProfileService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.errors import InvalidTokenError


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_auth_service(container: Container = Depends(get_container)) -> AuthService:
    return container.auth


def get_profile_service(container: Container = Depends(get_container)) -> ProfileService:
    return container.profiles


def get_doctor_service(container: Container = Depends(get_container)) -> DoctorService:
    return container.doctors


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


def _unauthenticated() -> HTTPException:
    return HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    request: Request, service: AuthService = Depends(get_auth_service)
) -> domain.User:
    """401 for any missing/bad/expired token or unknown/inactive user; role is read from the DB."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise _unauthenticated()
    try:
        return service.authenticate(token)
    except InvalidTokenError:
        raise _unauthenticated() from None


def require_roles(*roles: Role) -> Callable[[domain.User], domain.User]:
    """Dependency factory: 403 unless the authenticated user's stored role is listed."""
    allowed = frozenset(roles)

    def dependency(user: domain.User = Depends(get_current_user)) -> domain.User:
        if user.role not in allowed:
            raise HTTPException(status_code=403)
        return user

    return dependency
