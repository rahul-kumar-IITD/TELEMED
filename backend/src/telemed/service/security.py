"""argon2 password hashing and HS256 JWT issuing/decoding."""
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from telemed.types.domain import AccessToken, TokenClaims
from telemed.types.errors import InvalidTokenError
from telemed.types.ids import UserId

_ALGORITHM = "HS256"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@cache
def dummy_hash() -> str:
    """A valid hash nobody knows the password of, verified when the account cannot log in."""
    return hash_password(secrets.token_urlsafe(32))


def issue_token(
    user_id: UserId, role: str, secret: str, now: datetime, lifetime_minutes: int
) -> AccessToken:
    expires_at = now + timedelta(minutes=lifetime_minutes)
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return AccessToken(
        access_token=jwt.encode(claims, secret, algorithm=_ALGORITHM),
        token_type="bearer",
        expires_in=lifetime_minutes * 60,
        expires_at=expires_at,
    )


def decode_token(token: str, secret: str, now: datetime) -> TokenClaims:
    """Validate signature and expiry against the injected `now`; raises InvalidTokenError."""
    try:
        claims = jwt.decode(
            token, secret, algorithms=[_ALGORITHM],
            options={
                "verify_exp": False,  # expiry is checked below against the injected clock
                "verify_iat": False,
                "require": ["sub", "exp", "iat", "jti"],
            },
        )
        expires_at = datetime.fromtimestamp(int(claims["exp"]), UTC)
        if expires_at <= now:
            raise InvalidTokenError("token expired")
        return TokenClaims(
            user_id=UserId(int(claims["sub"])), role=str(claims.get("role", "")),
            expires_at=expires_at,
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError("invalid token") from exc
