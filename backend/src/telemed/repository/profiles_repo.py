"""patient_profiles and append-only patient_profile_versions."""
from datetime import datetime

from sqlalchemy.orm import Session

from telemed.repository.models import PatientProfile, PatientProfileVersion
from telemed.types.domain import ProfileData
from telemed.types.ids import UserId


def insert_patient_profile(session: Session, patient_id: UserId, now: datetime) -> None:
    session.add(PatientProfile(patient_id=patient_id, created_at=now))
    session.flush()


def insert_version(
    session: Session,
    patient_id: UserId,
    version_number: int,
    data: ProfileData,
    changed_by: UserId,
    now: datetime,
) -> None:
    session.add(
        PatientProfileVersion(
            patient_id=patient_id, version_number=version_number, full_name=data.full_name,
            age=data.age, gender=data.gender.value, phone=data.phone,
            changed_by_user_id=changed_by, created_at=now,
        )
    )
    session.flush()
