"""E1-S2 AC3: every log line is JSON with correlation_id and contains no PHI."""
import io
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from telemed.api.app import create_app
from telemed.config.logging import configure_logging, get_correlation_id

EMAIL = "phi.person@example.test"
NAME = "Zebediah Quillfeather"
NOTE = "secret note text 9137"


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    app_root = logging.getLogger()
    saved_handlers, saved_level = list(app_root.handlers), app_root.level
    configure_logging(stream=buffer)
    yield buffer
    app_root.handlers[:] = saved_handlers
    app_root.setLevel(saved_level)


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


@pytest.mark.ac("AC-E1-S2-3")
def test_request_with_phi_body_logs_json_without_phi(stream: io.StringIO) -> None:
    app: FastAPI = create_app()  # bootstrap() reconfigures logging to stdout ...
    configure_logging(stream=stream)  # ... so capture into the buffer afterwards
    logging.getLogger("httpx").setLevel(logging.WARNING)  # test-client noise, not the app

    @app.post("/t/phi")
    async def phi() -> None:
        raise RuntimeError(f"{EMAIL} {NAME} {NOTE}")

    client = TestClient(app, raise_server_exceptions=False)
    body = {"email": EMAIL, "full_name": NAME, "text": NOTE}
    client.post("/health", json=body, headers={"X-Request-ID": "log-check-1"})
    client.post("/t/phi?email=" + EMAIL, json=body, headers={"X-Request-ID": "log-check-2"})
    raw = stream.getvalue()
    lines = _lines(stream)
    assert lines
    assert all("correlation_id" in line for line in lines)
    for line in lines:
        assert line["correlation_id"] in {"log-check-1", "log-check-2"}
    assert {line["correlation_id"] for line in lines} == {"log-check-1", "log-check-2"}
    for secret in (EMAIL, NAME, NOTE, "phi.person"):
        assert secret not in raw
    failure = [line for line in lines if line["event"] == "unhandled_exception"]
    assert failure[0]["error_class"] == "RuntimeError"
    assert any(
        line["event"] == "request_completed" and line["path_template"] == "/health"
        and line["status_code"] == 405 for line in lines
    )


@pytest.mark.ac("AC-E1-S2-3")
def test_non_whitelisted_extra_fields_are_dropped(stream: io.StringIO) -> None:
    logging.getLogger("telemed.test").info(
        "something_happened", extra={"user_id": 7, "email": EMAIL, "full_name": NAME}
    )
    (line,) = _lines(stream)
    assert line["user_id"] == 7
    assert "email" not in line and "full_name" not in line
    assert line["correlation_id"] == "-"
    assert EMAIL not in stream.getvalue()


def test_uvicorn_loggers_use_json_and_access_log_disabled(stream: io.StringIO) -> None:
    logging.getLogger("uvicorn.error").info("Started server process")
    logging.getLogger("uvicorn.access").info("127.0.0.1 - GET /health")
    lines = _lines(stream)
    assert [line["event"] for line in lines] == ["Started server process"]
    assert get_correlation_id() == "-"


def test_configure_logging_is_idempotent(stream: io.StringIO) -> None:
    configure_logging(stream=stream)
    configure_logging(stream=stream)
    logging.getLogger("telemed.test").info("once")
    assert [line["event"] for line in _lines(stream)] == ["once"]
