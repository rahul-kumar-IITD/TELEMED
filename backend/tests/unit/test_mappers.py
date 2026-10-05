"""E1-S1 AC3 persistence leg: fee persisted as integer minor units, read back as Decimal."""
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from telemed.repository import models
from telemed.repository.mappers import (
    appointment_to_domain,
    doctor_to_domain,
    slot_to_domain,
    user_to_domain,
)
from telemed.types.enums import AppointmentStatus, Role, SlotStatus
from telemed.types.money import to_minor

NOW = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)


@pytest.mark.ac("AC-E1-S1-3")
def test_fee_persisted_as_integer_and_read_back_as_decimal(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            models.User(
                user_id=2, email="d@example.test", password_hash="$argon2id$x",
                role="DOCTOR", created_at=NOW, updated_at=NOW,
            )
        )
        session.add(
            models.User(
                user_id=1, email="p@example.test", password_hash="$argon2id$x",
                role="PATIENT", created_at=NOW, updated_at=NOW,
            )
        )
        session.flush()
        session.add(models.PatientProfile(patient_id=1, created_at=NOW))
        session.add(
            models.DoctorProfile(
                doctor_id=2, full_name="Dr D", specialty="Cardiology",
                languages=json.dumps(["en", "hi"]), fee_minor=to_minor(Decimal("500.00")),
                created_at=NOW, updated_at=NOW,
            )
        )
        session.flush()
        session.add(
            models.Slot(
                slot_id=1, doctor_id=2, start_time=NOW,
                end_time=datetime(2026, 10, 5, 10, 30, tzinfo=UTC), created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        session.add(
            models.Appointment(
                appointment_id=1, patient_id=1, doctor_id=2, slot_id=1,
                fee_minor=50000, created_at=NOW, updated_at=NOW,
            )
        )
        session.commit()
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT fee_minor, typeof(fee_minor) FROM doctor_profiles"))
        assert stored.one() == (50000, "integer")
    with Session(engine) as session:
        doctor = session.get(models.DoctorProfile, 2)
        assert doctor is not None
        domain_doctor = doctor_to_domain(doctor)
        assert domain_doctor.fee == Decimal("500.00")
        assert domain_doctor.languages == ("en", "hi")
        slot = session.get(models.Slot, 1)
        assert slot is not None
        assert slot_to_domain(slot).status is SlotStatus.AVAILABLE
        assert slot_to_domain(slot).start_time == NOW
        appt = session.get(models.Appointment, 1)
        assert appt is not None
        assert appointment_to_domain(appt).fee == Decimal("500.00")
        assert appointment_to_domain(appt).status is AppointmentStatus.BOOKED
        user = session.get(models.User, 2)
        assert user is not None
        assert user_to_domain(user).role is Role.DOCTOR
        assert user_to_domain(user).active is True


def test_utc_datetime_rejects_naive(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(models.PatientProfile(patient_id=1, created_at=datetime(2026, 1, 1)))
        with pytest.raises(Exception, match="naive datetime"):
            session.flush()
