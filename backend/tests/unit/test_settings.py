"""E1-S2 AC5: settings come from the environment; unknown timezone aborts startup."""
import pytest
from pydantic import ValidationError

from telemed.config.settings import Settings, load_settings
from telemed.service.bootstrap import bootstrap

_VARS = ("PROVIDER_TIMEZONE", "JWT_LIFETIME_MINUTES", "DATABASE_PATH", "BUSY_TIMEOUT_MS")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.ac("AC-E1-S2-5")
def test_defaults() -> None:
    settings = load_settings()
    assert settings.provider_timezone == "UTC"
    assert settings.jwt_lifetime_minutes == 30
    assert settings.database_path == "./telemed.db"
    assert settings.busy_timeout_ms == 10000


@pytest.mark.ac("AC-E1-S2-5")
def test_env_values_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_TIMEZONE", "Asia/Kolkata")
    monkeypatch.setenv("JWT_LIFETIME_MINUTES", "15")
    monkeypatch.setenv("DATABASE_PATH", "/tmp/x.db")
    monkeypatch.setenv("BUSY_TIMEOUT_MS", "7000")
    settings = Settings()
    assert settings.provider_timezone == "Asia/Kolkata"
    assert settings.jwt_lifetime_minutes == 15
    assert settings.database_path == "/tmp/x.db"
    assert settings.busy_timeout_ms == 7000


@pytest.mark.ac("AC-E1-S2-5")
def test_unknown_timezone_aborts_naming_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_TIMEZONE", "Not/AZone")
    with pytest.raises(ValidationError, match="PROVIDER_TIMEZONE"):
        load_settings()
    with pytest.raises(ValidationError, match="PROVIDER_TIMEZONE"):
        bootstrap()


@pytest.mark.parametrize(
    ("name", "value"),
    [("BUSY_TIMEOUT_MS", "100"), ("JWT_LIFETIME_MINUTES", "0")],
)
def test_out_of_range_values_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        load_settings()
