"""appointments queries."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from telemed.repository.mappers import appointment_to_domain
from telemed.repository.models import Appointment
from telemed.types import domain
from telemed.types.enums import AppointmentStatus
from telemed.types.ids import SlotId, UserId
from telemed.types.money import to_minor


def insert_booked(
    session: Session, patient_id: UserId, doctor_id: UserId, slot_id: SlotId, fee: Decimal,
    now: datetime,
) -> domain.Appointment:
    """Insert a BOOKED appointment carrying the fee snapshot."""
    row = Appointment(
        patient_id=patient_id, doctor_id=doctor_id, slot_id=slot_id,
        status=AppointmentStatus.BOOKED.value, fee_minor=to_minor(fee),
        created_at=now, updated_at=now,
    )
    session.add(row)
    session.flush()
    return appointment_to_domain(row)
