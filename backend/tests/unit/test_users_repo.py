"""users_repo: duplicate-email race mapping and clock basics."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from telemed.config.clock import SystemClock
from telemed.repository import users_repo
from telemed.types.enums import Role
from telemed.types.errors import EmailAlreadyRegisteredException

NOW = datetime(2026, 10, 6, tzinfo=UTC)
HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


def test_unique_violation_maps_to_email_already_registered(engine: Engine) -> None:
    with Session(engine) as session:
        users_repo.insert_user(session, "A@Example.test", HASH, Role.PATIENT, NOW)
        with pytest.raises(EmailAlreadyRegisteredException):
            users_repo.insert_user(session, "a@example.test", HASH, Role.PATIENT, NOW)


def test_other_integrity_errors_are_not_masked(engine: Engine) -> None:
    with Session(engine) as session, pytest.raises(IntegrityError):
        users_repo.insert_user(session, "b@example.test", "plaintext", Role.PATIENT, NOW)


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None and now.utcoffset().total_seconds() == 0  # type: ignore[union-attr]
