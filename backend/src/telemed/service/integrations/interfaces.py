"""Integration seams (video, payment, e-prescription, notification).

Implementations are injected; the default ones are the stubs in `stubs.py`.
"""
from decimal import Decimal
from typing import Protocol

from telemed.types.enums import EventType
from telemed.types.ids import AppointmentId


class VideoService(Protocol):
    def join_url(self, appointment_id: AppointmentId) -> str: ...


class PaymentService(Protocol):
    def charge(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        """Returns a payment reference."""
        ...

    def refund(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        """Returns a refund reference."""
        ...


class PrescriptionService(Protocol):
    def issue(self, appointment_id: AppointmentId) -> str:
        """Returns a prescription reference."""
        ...


class NotificationService(Protocol):
    def notify(self, appointment_id: AppointmentId, event_type: EventType) -> None: ...
