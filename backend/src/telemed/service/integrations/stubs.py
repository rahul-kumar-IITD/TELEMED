"""Default stub integrations: deterministic results and one identifier-only log line per call.

Stubs never touch the appointment event log or the database.
"""
import logging
from decimal import Decimal

from telemed.types.enums import EventType
from telemed.types.ids import AppointmentId

_logger = logging.getLogger("telemed.integrations")


def _log(event: str, appointment_id: AppointmentId, event_type: EventType | None = None) -> None:
    extra: dict[str, object] = {"appointment_id": appointment_id}
    if event_type is not None:
        extra["event_type"] = event_type.value
    _logger.info(event, extra=extra)


class StubVideoService:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def join_url(self, appointment_id: AppointmentId) -> str:
        _log("stub_video_join_url", appointment_id)
        return f"{self._base_url}/{appointment_id}"


class StubPaymentService:
    def charge(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        _log("stub_payment_charge", appointment_id)
        return f"stub-charge-{appointment_id}"

    def refund(self, appointment_id: AppointmentId, amount: Decimal) -> str:
        _log("stub_payment_refund", appointment_id)
        return f"stub-refund-{appointment_id}"


class StubPrescriptionService:
    def issue(self, appointment_id: AppointmentId) -> str:
        _log("stub_prescription_issue", appointment_id)
        return f"stub-rx-{appointment_id}"


class StubNotificationService:
    def notify(self, appointment_id: AppointmentId, event_type: EventType) -> None:
        _log("stub_notification_sent", appointment_id, event_type)
