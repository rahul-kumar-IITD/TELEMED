"""Slot response models (API-11, API-12, API-13, API-14)."""
from datetime import datetime

from pydantic import BaseModel

from telemed.types import domain


class SlotOut(BaseModel):
    slot_id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    status: str

    @classmethod
    def from_domain(cls, slot: domain.Slot) -> "SlotOut":
        return cls(
            slot_id=slot.slot_id, doctor_id=slot.doctor_id, start_time=slot.start_time,
            end_time=slot.end_time, status=slot.status.value,
        )


class SlotListResponse(BaseModel):
    items: list[SlotOut]
    total: int

    @classmethod
    def from_domain(cls, slots: list[domain.Slot]) -> "SlotListResponse":
        items = [SlotOut.from_domain(slot) for slot in slots]
        return cls(items=items, total=len(items))
