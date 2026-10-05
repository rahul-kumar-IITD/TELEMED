"""E1-S3 AC5/AC6: argon2 hashing and JWT issuing/decoding."""
from datetime import UTC, datetime, timedelta

import pytest

from telemed.service import security
from telemed.types.errors import InvalidTokenError
from telemed.types.ids import UserId

SECRET = "unit-test-secret-at-least-32-bytes-long-0123"
NOW = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)


@pytest.mark.ac("AC-E1-S3-5")
def test_hash_is_argon2_and_not_plaintext() -> None:
    hashed = security.hash_password("Passw0rd!")
    assert hashed.startswith("$argon2")
    assert hashed != "Passw0rd!"
    assert security.hash_password("Passw0rd!") != hashed  # salted


def test_verify_password_matches_and_mismatches() -> None:
    hashed = security.hash_password("Passw0rd!")
    assert security.verify_password("Passw0rd!", hashed) is True
    assert security.verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_malformed_hash() -> None:
    assert security.verify_password("x", "not-a-hash") is False


def test_dummy_hash_never_verifies() -> None:
    assert security.verify_password("anything", security.dummy_hash()) is False


@pytest.mark.ac("AC-E1-S3-6")
def test_token_round_trip_and_expiry_metadata() -> None:
    token = security.issue_token(UserId(7), "PATIENT", SECRET, NOW, 30)
    assert token.token_type == "bearer"
    assert token.expires_in == 1800
    assert token.expires_at == NOW + timedelta(minutes=30)
    assert len(token.access_token.split(".")) == 3
    claims = security.decode_token(token.access_token, SECRET, NOW)
    assert claims.user_id == UserId(7)
    assert claims.role == "PATIENT"
    assert claims.expires_at == NOW + timedelta(minutes=30)


def test_tokens_have_unique_ids() -> None:
    first = security.issue_token(UserId(1), "PATIENT", SECRET, NOW, 30)
    second = security.issue_token(UserId(1), "PATIENT", SECRET, NOW, 30)
    assert first.access_token != second.access_token


def test_expired_token_rejected() -> None:
    token = security.issue_token(UserId(7), "PATIENT", SECRET, NOW, 30)
    with pytest.raises(InvalidTokenError):
        security.decode_token(token.access_token, SECRET, NOW + timedelta(minutes=31))


def test_wrong_secret_and_garbage_rejected() -> None:
    token = security.issue_token(UserId(7), "PATIENT", SECRET, NOW, 30)
    with pytest.raises(InvalidTokenError):
        security.decode_token(token.access_token, SECRET + "x", NOW)
    with pytest.raises(InvalidTokenError):
        security.decode_token("garbage", SECRET, NOW)
