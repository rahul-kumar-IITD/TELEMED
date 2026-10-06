"""E1-S2 AC5: settings come from the environment; unknown timezone aborts startup."""
import pytest
from pydantic import ValidationError

from telemed.config.settings import Settings, load_settings
from telemed.service.bootstrap import bootstrap

_VARS = (
    "PROVIDER_TIMEZONE", "JWT_LIFETIME_MINUTES", "DATABASE_PATH", "BUSY_TIMEOUT_MS",
    "JWT_SECRET", "VIDEO_BASE_URL", "APP_ENV",
)


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


OLD_DEV_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"


def test_jwt_secret_default_is_long_enough_and_hidden() -> None:
    settings = load_settings()  # APP_ENV defaults to dev: random per-process secret
    secret = settings.jwt_secret.get_secret_value()
    assert len(secret.encode()) >= 32
    assert secret != OLD_DEV_SECRET
    assert settings.video_base_url == "https://video.example.test/visit"
    assert secret not in repr(settings)


@pytest.mark.nfr("NFR-04")
def test_nfr04_dev_secret_is_random_per_settings_instance() -> None:
    assert load_settings().jwt_secret.get_secret_value() != (
        load_settings().jwt_secret.get_secret_value()
    )


@pytest.mark.nfr("NFR-04")
@pytest.mark.parametrize("env", ["staging", "prod"])
def test_nfr04_missing_secret_refused_outside_dev(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("APP_ENV", env)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        load_settings()
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        bootstrap()


@pytest.mark.nfr("NFR-04")
@pytest.mark.parametrize("env", ["staging", "prod"])
def test_nfr04_old_dev_default_refused_outside_dev_without_echo(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("JWT_SECRET", OLD_DEV_SECRET)
    with pytest.raises(ValidationError, match="JWT_SECRET") as info:
        load_settings()
    assert OLD_DEV_SECRET not in str(info.value)


@pytest.mark.nfr("NFR-04")
def test_nfr04_explicit_secret_accepted_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "s" * 40)
    assert load_settings().jwt_secret.get_secret_value() == "s" * 40


@pytest.mark.nfr("NFR-04")
def test_nfr04_unknown_app_env_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValidationError, match="APP_ENV|app_env"):
        load_settings()


@pytest.mark.nfr("NFR-04")
def test_nfr04_blank_secret_in_dev_gets_random_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "")
    assert len(load_settings().jwt_secret.get_secret_value().encode()) >= 32


def test_short_jwt_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        load_settings()
