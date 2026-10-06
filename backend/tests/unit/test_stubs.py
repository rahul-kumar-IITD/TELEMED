"""E3-S1: stub integrations behind injectable interfaces."""
import io
import json
import logging
from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from telemed.api import deps
from telemed.api.app import create_app
from telemed.config.logging import configure_logging
from telemed.repository.models import AppointmentEvent
from telemed.service.integrations import stubs
from telemed.service.integrations.interfaces import (
    NotificationService,
    PaymentService,
    PrescriptionService,
    VideoService,
)
from telemed.types.enums import EventType
from telemed.types.ids import AppointmentId
from tests.conftest import Spies

APPT = AppointmentId(42)
BASE = "https://video.example.test/visit"


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    root = logging.getLogger()
    saved, level = list(root.handlers), root.level
    configure_logging(stream=buffer)
    yield buffer
    root.handlers[:] = saved
    root.setLevel(level)


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def _call_everything() -> None:
    stubs.StubVideoService(BASE).join_url(APPT)
    stubs.StubPaymentService().charge(APPT, Decimal("500.00"))
    stubs.StubPaymentService().refund(APPT, Decimal("500.00"))
    stubs.StubPrescriptionService().issue(APPT)
    stubs.StubNotificationService().notify(APPT, EventType.BOOKED)


@pytest.mark.ac("AC-E3-S1-1")
def test_stubs_satisfy_the_interfaces() -> None:
    video: VideoService = stubs.StubVideoService(BASE)
    payment: PaymentService = stubs.StubPaymentService()
    prescription: PrescriptionService = stubs.StubPrescriptionService()
    notification: NotificationService = stubs.StubNotificationService()
    assert video and payment and prescription and notification


@pytest.mark.ac("AC-E3-S1-1")
def test_default_wiring_binds_a_stub_for_each_integration() -> None:
    app = create_app()
    assert app.dependency_overrides == {}
    container = app.state.container
    assert isinstance(deps.get_video_service(container), stubs.StubVideoService)
    assert isinstance(deps.get_payment_service(container), stubs.StubPaymentService)
    assert isinstance(deps.get_prescription_service(container), stubs.StubPrescriptionService)
    assert isinstance(deps.get_notification_service(container), stubs.StubNotificationService)


@pytest.mark.ac("AC-E3-S1-1")
def test_default_wiring_resolves_through_http_dependencies() -> None:
    app = create_app()

    @app.get("/t/wiring")
    async def wiring(
        video: VideoService = Depends(deps.get_video_service),
        payment: PaymentService = Depends(deps.get_payment_service),
        prescription: PrescriptionService = Depends(deps.get_prescription_service),
        notification: NotificationService = Depends(deps.get_notification_service),
    ) -> list[str]:
        return [type(x).__name__ for x in (video, payment, prescription, notification)]

    assert TestClient(app).get("/t/wiring").json() == [
        "StubVideoService",
        "StubPaymentService",
        "StubPrescriptionService",
        "StubNotificationService",
    ]


@pytest.mark.ac("AC-E3-S1-2")
def test_each_call_emits_exactly_one_identifier_only_json_line(
    log_stream: io.StringIO,
) -> None:
    calls = [
        lambda: stubs.StubVideoService(BASE).join_url(APPT),
        lambda: stubs.StubPaymentService().charge(APPT, Decimal("500.00")),
        lambda: stubs.StubPaymentService().refund(APPT, Decimal("500.00")),
        lambda: stubs.StubPrescriptionService().issue(APPT),
        lambda: stubs.StubNotificationService().notify(APPT, EventType.CANCELLED),
    ]
    for call in calls:
        before = len(_lines(log_stream))
        call()
        lines = _lines(log_stream)
        assert len(lines) == before + 1
        assert lines[-1]["appointment_id"] == 42
        assert set(lines[-1]) <= {
            "timestamp", "level", "event", "correlation_id", "appointment_id", "event_type",
        }
    assert "500" not in log_stream.getvalue()
    assert _lines(log_stream)[-1]["event_type"] == "CANCELLED"


@pytest.mark.ac("AC-E3-S1-3")
def test_stub_calls_leave_appointment_events_unchanged(engine: Engine) -> None:
    def count() -> int:
        with Session(engine) as session:
            return int(session.scalar(select(func.count()).select_from(AppointmentEvent)) or 0)

    before = count()
    _call_everything()
    assert count() == before


@pytest.mark.ac("AC-E3-S1-4")
def test_video_join_url_is_deterministic_and_contains_appointment_id() -> None:
    video = stubs.StubVideoService(BASE + "/")
    first, second = video.join_url(APPT), video.join_url(APPT)
    assert first == second == f"{BASE}/42"
    assert video.join_url(AppointmentId(43)) != first


@pytest.mark.ac("AC-E3-S1-5")
def test_spies_override_stubs_through_dependency_injection(
    app_with_spies: FastAPI, spies: Spies
) -> None:
    app = app_with_spies

    @app.post("/t/use")
    async def use(
        video: VideoService = Depends(deps.get_video_service),
        payment: PaymentService = Depends(deps.get_payment_service),
        prescription: PrescriptionService = Depends(deps.get_prescription_service),
        notification: NotificationService = Depends(deps.get_notification_service),
    ) -> dict[str, str]:
        notification.notify(APPT, EventType.BOOKED)
        return {
            "url": video.join_url(APPT),
            "charge": payment.charge(APPT, Decimal("1.00")),
            "refund": payment.refund(APPT, Decimal("1.00")),
            "rx": prescription.issue(APPT),
        }

    body = TestClient(app).post("/t/use").json()
    assert body == {
        "url": "spy://42", "charge": "spy-charge", "refund": "spy-refund", "rx": "spy-rx",
    }
    assert spies.video.calls == [("join_url", APPT)]
    assert spies.payment.calls == [
        ("charge", APPT, Decimal("1.00")),
        ("refund", APPT, Decimal("1.00")),
    ]
    assert spies.prescription.calls == [("issue", APPT)]
    assert spies.notification.calls == [("notify", APPT, EventType.BOOKED)]
