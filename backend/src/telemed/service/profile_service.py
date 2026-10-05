"""Versioned patient profile writes (initial version at registration)."""
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.repository import profiles_repo
from telemed.types.domain import ProfileData
from telemed.types.ids import UserId

INITIAL_VERSION = 1


def create_initial_profile(
    session: Session, patient_id: UserId, data: ProfileData, now: datetime
) -> None:
    """Insert the patient profile row and its version 1 inside the given transaction."""
    profiles_repo.insert_patient_profile(session, patient_id, now)
    profiles_repo.insert_version(session, patient_id, INITIAL_VERSION, data, patient_id, now)
