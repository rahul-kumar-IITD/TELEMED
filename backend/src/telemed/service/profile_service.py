"""Versioned patient profiles: initial version, current-version reads, partial updates."""
import dataclasses
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.config.clock import Clock
from telemed.repository import profiles_repo
from telemed.service import access
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.domain import PatientProfileView, ProfileChanges, ProfileData
from telemed.types.enums import Role
from telemed.types.errors import ForbiddenException, NotFoundException
from telemed.types.ids import UserId

INITIAL_VERSION = 1

_logger = logging.getLogger("telemed.profile")


def create_initial_profile(
    session: Session, patient_id: UserId, data: ProfileData, now: datetime
) -> None:
    """Insert the patient profile row and its version 1 inside the given transaction."""
    profiles_repo.insert_patient_profile(session, patient_id, now)
    profiles_repo.insert_version(session, patient_id, INITIAL_VERSION, data, patient_id, now)


def _merge(current: ProfileData, changes: ProfileChanges) -> ProfileData:
    carried = {k: v for k, v in dataclasses.asdict(changes).items() if v is not None}
    return dataclasses.replace(current, **carried)


class ProfileService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def get_own(self, actor: domain.User) -> PatientProfileView:
        """The actor's current profile (the router restricts this to PATIENT)."""
        return self.get_for(actor, actor.user_id)

    def get_for(self, actor: domain.User, patient_id: UserId) -> PatientProfileView:
        """Current profile of `patient_id`: owner or ADMIN; foreign/non-patient ids are 404."""
        with self._uow.read() as session:
            latest = profiles_repo.latest_version(session, patient_id)
        access.ensure_can_read(actor, None if latest is None else [patient_id])
        assert latest is not None  # ensure_can_read raised for None
        return latest

    def update(
        self, actor: domain.User, patient_id: UserId, changes: ProfileChanges
    ) -> PatientProfileView:
        """Insert a new version merged onto the latest one; owner patient or ADMIN only."""
        owner = actor.role is Role.PATIENT and actor.user_id == patient_id
        if not (owner or actor.role is Role.ADMIN):
            raise ForbiddenException()
        now = self._clock.now()
        with self._uow.transaction() as session:
            latest = profiles_repo.latest_version(session, patient_id)
            if latest is None:
                raise NotFoundException()
            version = latest.version_number + 1
            merged = _merge(latest.data, changes)
            profiles_repo.insert_version(session, patient_id, version, merged, actor.user_id, now)
        _logger.info(
            "profile_updated", extra={"user_id": actor.user_id, "version_number": version}
        )
        return PatientProfileView(patient_id, version, merged, now)
