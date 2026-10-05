"""Admin endpoints; the whole router is ADMIN-only."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_doctor_service, require_roles
from telemed.api.schemas.admin import OnboardDoctorRequest, OnboardDoctorResponse
from telemed.service.doctor_service import DoctorService
from telemed.types.enums import Role

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("/doctors", status_code=201)
def onboard_doctor(
    body: OnboardDoctorRequest, service: DoctorService = Depends(get_doctor_service)
) -> OnboardDoctorResponse:
    created = service.onboard(body.details(), body.initial_password)
    return OnboardDoctorResponse.from_domain(created)
