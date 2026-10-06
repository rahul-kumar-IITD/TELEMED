"""Synthetic data builders (all emails @example.test)."""
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from telemed.repository.models import AvailabilityTemplate, DoctorProfile, User

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHQ$ZmFrZWhhc2g"


def add_doctor(
    engine: Engine,
    email: str,
    templates: list[tuple[int, str, str, int]],
    active: bool = True,
) -> int:
    """Insert a doctor with (weekday, start, end, slot_minutes) templates; returns doctor_id."""
    with Session(engine) as session, session.begin():
        user = User(
            email=email, password_hash=_HASH, role="DOCTOR", active=int(active),
            created_at=_EPOCH, updated_at=_EPOCH,
        )
        session.add(user)
        session.flush()
        session.add(
            DoctorProfile(
                doctor_id=user.user_id, full_name="Dr Test", specialty="General",
                languages='["en"]', fee_minor=50000, created_at=_EPOCH, updated_at=_EPOCH,
            )
        )
        session.flush()
        for weekday, start, end, length in templates:
            session.add(
                AvailabilityTemplate(
                    doctor_id=user.user_id, weekday=weekday, start_time=start, end_time=end,
                    slot_length_minutes=length, created_at=_EPOCH,
                )
            )
        return int(user.user_id)
