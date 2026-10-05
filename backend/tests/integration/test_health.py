"""E1-S2 AC1: GET /health returns 200 {"status":"ok"} quickly."""
import time

import pytest
from fastapi.testclient import TestClient

from telemed.api.app import create_app


@pytest.mark.ac("AC-E1-S2-1")
def test_health_ok_within_one_second() -> None:
    started = time.perf_counter()
    client = TestClient(create_app())
    response = client.get("/health")
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.text == '{"status":"ok"}'
    assert elapsed < 1.0
