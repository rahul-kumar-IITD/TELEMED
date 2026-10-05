"""users table queries."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from telemed.repository.mappers import user_to_domain
from telemed.repository.models import User as UserRow
from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.errors import EmailAlreadyRegisteredException


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
