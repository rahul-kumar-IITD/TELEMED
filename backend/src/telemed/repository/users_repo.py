"""users table queries."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from telemed.repository.mappers import user_to_domain
from telemed.repository.models import DoctorProfile as DoctorProfileRow
from telemed.repository.models import PatientProfileVersion
from telemed.repository.models import User as UserRow
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.errors import EmailAlreadyRegisteredException
from telemed.types.ids import UserId


@dataclass(frozen=True)
class UserCredentials:
    """A user together with the stored hash; never leaves the service layer."""

    user: domain.User
    password_hash: str


def find_credentials_by_email(session: Session, email: str) -> UserCredentials | None:
    row = session.scalars(select(UserRow).where(UserRow.email == email.lower())).first()
    if row is None:
        return None
    return UserCredentials(user=user_to_domain(row), password_hash=row.password_hash)


def find_by_id(session: Session, user_id: UserId) -> domain.User | None:
    row = session.get(UserRow, user_id)
    return user_to_domain(row) if row is not None else None


def find_full_name(session: Session, user: domain.User) -> str | None:
    """Display name from the latest patient profile version or the doctor profile; admins: None."""
    if user.role is Role.PATIENT:
        return session.scalars(
            select(PatientProfileVersion.full_name)
            .where(PatientProfileVersion.patient_id == user.user_id)
            .order_by(PatientProfileVersion.version_number.desc())
            .limit(1)
        ).first()
    if user.role is Role.DOCTOR:
        return session.scalars(
            select(DoctorProfileRow.full_name).where(DoctorProfileRow.doctor_id == user.user_id)
        ).first()
    return None


def insert_user(
    session: Session, email: str, password_hash: str, role: Role, now: datetime
) -> domain.User:
    """Insert one user; a duplicate (lower-cased) email raises EmailAlreadyRegisteredException."""
    row = UserRow(
        email=email.lower(), password_hash=password_hash, role=role.value, active=1,
        created_at=now, updated_at=now,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        if "users.email" not in str(exc.orig):
            raise
        raise EmailAlreadyRegisteredException() from exc
    return user_to_domain(row)


def list_users(session: Session, role: Role | None, active: bool | None) -> list[domain.User]:
    """All users ordered by user_id, optionally filtered by role and active flag."""
    stmt = select(UserRow).order_by(UserRow.user_id)
    if role is not None:
        stmt = stmt.where(UserRow.role == role.value)
    if active is not None:
        stmt = stmt.where(UserRow.active == int(active))
    return [user_to_domain(row) for row in session.scalars(stmt)]


def set_active(session: Session, user_id: UserId, active: bool, now: datetime) -> None:
    session.execute(
        update(UserRow).where(UserRow.user_id == user_id).values(active=int(active), updated_at=now)
    )
