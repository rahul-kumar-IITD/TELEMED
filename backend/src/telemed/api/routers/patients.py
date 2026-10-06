"""Patient profile endpoints. Static /me routes are registered before /{patient_id}."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_profile_service, require_roles
from telemed.api.schemas.profile import PatientProfileResponse, ProfileUpdateRequest
from telemed.service.profile_service import ProfileService
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.ids import UserId

router = APIRouter(prefix="/api/patients")

_patient_only = require_roles(Role.PATIENT)
_patient_or_admin = require_roles(Role.PATIENT, Role.ADMIN)


@router.get("/me/profile")
def get_my_profile(
    user: domain.User = Depends(_patient_only),
    service: ProfileService = Depends(get_profile_service),
) -> PatientProfileResponse:
    return PatientProfileResponse.from_domain(service.get_own(user))


@router.put("/me/profile")
def update_my_profile(
    body: ProfileUpdateRequest,
    user: domain.User = Depends(_patient_only),
    service: ProfileService = Depends(get_profile_service),
) -> PatientProfileResponse:
    updated = service.update(user, user.user_id, body.changes())
    return PatientProfileResponse.from_domain(updated)


@router.get("/{patient_id}/profile")
def get_patient_profile(
    patient_id: int,
    user: domain.User = Depends(_patient_or_admin),
    service: ProfileService = Depends(get_profile_service),
) -> PatientProfileResponse:
    return PatientProfileResponse.from_domain(service.get_for(user, UserId(patient_id)))
