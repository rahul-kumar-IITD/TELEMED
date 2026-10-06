"""Doctor search and slot endpoints. Literal /me routes are registered before /{doctor_id}."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from telemed.api.deps import get_current_user, get_doctor_service, require_roles
from telemed.api.schemas.doctors import DoctorListResponse, DoctorSummaryOut
from telemed.api.schemas.slots import SlotListResponse, SlotOut
from telemed.service.doctor_service import DoctorService
from telemed.types import domain
from telemed.types.domain import DoctorSearch
from telemed.types.enums import DoctorSort, Role
from telemed.types.ids import SlotId, UserId

router = APIRouter(prefix="/api/doctors")

_doctor_only = require_roles(Role.DOCTOR)


@router.get("/me/slots")
def list_my_slots(
    range_from: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    range_to: Annotated[AwareDatetime | None, Query(alias="to")] = None,
    user: domain.User = Depends(_doctor_only),
    service: DoctorService = Depends(get_doctor_service),
) -> SlotListResponse:
    return SlotListResponse.from_domain(service.my_slots(user.user_id, range_from, range_to))


@router.put("/me/slots/{slot_id}/block")
def block_slot(
    slot_id: int,
    user: domain.User = Depends(_doctor_only),
    service: DoctorService = Depends(get_doctor_service),
) -> SlotOut:
    return SlotOut.from_domain(service.block_slot(user.user_id, SlotId(slot_id)))


@router.put("/me/slots/{slot_id}/unblock")
def unblock_slot(
    slot_id: int,
    user: domain.User = Depends(_doctor_only),
    service: DoctorService = Depends(get_doctor_service),
) -> SlotOut:
    return SlotOut.from_domain(service.unblock_slot(user.user_id, SlotId(slot_id)))


@router.get("")
def search_doctors(
    specialty: str | None = None,
    language: str | None = None,
    available_from: AwareDatetime | None = None,
    available_to: AwareDatetime | None = None,
    sort: DoctorSort = DoctorSort.EARLIEST_SLOT,
    _user: domain.User = Depends(get_current_user),
    service: DoctorService = Depends(get_doctor_service),
) -> DoctorListResponse:
    criteria = DoctorSearch(
        specialty=specialty, language=language, available_from=available_from,
        available_to=available_to, sort=sort,
    )
    return DoctorListResponse.from_domain(service.search(criteria))


@router.get("/{doctor_id}")
def get_doctor(
    doctor_id: int,
    _user: domain.User = Depends(get_current_user),
    service: DoctorService = Depends(get_doctor_service),
) -> DoctorSummaryOut:
    return DoctorSummaryOut.from_domain(service.get_doctor(UserId(doctor_id)))


@router.get("/{doctor_id}/slots")
def list_open_slots(
    doctor_id: int,
    _user: domain.User = Depends(get_current_user),
    service: DoctorService = Depends(get_doctor_service),
) -> SlotListResponse:
    return SlotListResponse.from_domain(service.open_slots(UserId(doctor_id)))
