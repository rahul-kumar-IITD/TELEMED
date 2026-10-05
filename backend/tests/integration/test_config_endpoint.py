"""API-02: GET /api/config exposes UI-facing constants (public)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from telemed.api.app import create_app


@pytest.mark.ac("AC-E5-S1-supporting")
def test_config_returns_timezone_and_windows(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "integration-secret-at-least-32-bytes-0123")
    monkeypatch.setenv("PROVIDER_TIMEZONE", "Asia/Kolkata")
    with TestClient(create_app()) as client:
        response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {
        "provider_timezone": "Asia/Kolkata", "slot_window_days": 14, "change_window_minutes": 60,
    }
