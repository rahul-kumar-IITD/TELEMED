"""Admin endpoints; the whole router is ADMIN-only."""
from fastapi import APIRouter, Depends

from telemed.api.deps import (
    get_current_user,
    get_doctor_service,
    get_profile_service,
    get_user_admin_service,
    require_roles,
)
from telemed.api.schemas.admin import OnboardDoctorRequest, OnboardDoctorResponse, UserListResponse
from telemed.api.schemas.auth import UserResponse
from telemed.api.schemas.profile import PatientProfileResponse, ProfileUpdateRequest
from telemed.service.doctor_service import DoctorService
from telemed.service.profile_service import ProfileService
from telemed.service.user_admin_service import UserAdminService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import UserId

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("/doctors", status_code=201)
def onboard_doctor(
    body: OnboardDoctorRequest, service: DoctorService = Depends(get_doctor_service)
) -> OnboardDoctorResponse:
    created = service.onboard(body.details(), body.initial_password)
    return OnboardDoctorResponse.from_domain(created)


@router.get("/users")
def list_users(
    role: Role | None = None,
    active: bool | None = None,
    service: UserAdminService = Depends(get_user_admin_service),
) -> UserListResponse:
    return UserListResponse.from_domain(service.list_users(role, active))


@router.put("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    admin: domain.User = Depends(get_current_user),
    service: UserAdminService = Depends(get_user_admin_service),
) -> UserResponse:
    return UserResponse.from_domain(service.deactivate(admin, UserId(user_id)))


@router.put("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: int, service: UserAdminService = Depends(get_user_admin_service)
) -> UserResponse:
    return UserResponse.from_domain(service.reactivate(UserId(user_id)))


@router.put("/patients/{patient_id}/profile")
def update_patient_profile(
    patient_id: int,
    body: ProfileUpdateRequest,
    admin: domain.User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PatientProfileResponse:
    updated = service.update(admin, UserId(patient_id), body.changes())
    return PatientProfileResponse.from_domain(updated)
