"""Patient registration and login."""
import logging

from telemed.config.clock import Clock
from telemed.repository import users_repo
from telemed.service import profile_service, security
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.domain import LoginResult, ProfileData, UserView
from telemed.types.enums import Role
from telemed.types.errors import (
    EmailAlreadyRegisteredException,
    InvalidCredentialsException,
    InvalidTokenError,
)
from telemed.types.ids import UserId

_MAX_USER_ID = 2**63 - 1

_logger = logging.getLogger("telemed.auth")


class AuthService:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        jwt_secret: str,
        jwt_lifetime_minutes: int,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._jwt_secret = jwt_secret
        self._jwt_lifetime_minutes = jwt_lifetime_minutes

    def register(self, email: str, password: str, profile: ProfileData) -> domain.User:
        """Create a PATIENT (role is never caller-controlled) plus profile version 1."""
        password_hash = security.hash_password(password)  # before the write lock is taken
        now = self._clock.now()
        with self._uow.transaction() as session:
            if users_repo.find_credentials_by_email(session, email) is not None:
                raise EmailAlreadyRegisteredException()
            user = users_repo.insert_user(session, email, password_hash, Role.PATIENT, now)
            profile_service.create_initial_profile(session, user.user_id, profile, now)
        _logger.info("patient_registered", extra={"user_id": user.user_id})
        return user

    def login(self, email: str, password: str) -> LoginResult:
        """Verify credentials; every failure mode raises the same InvalidCredentialsException."""
        with self._uow.read() as session:
            found = users_repo.find_credentials_by_email(session, email)
        stored = found.password_hash if found is not None else security.dummy_hash()
        password_ok = security.verify_password(password, stored)  # always does hashing work
        if found is None or not found.user.active or not password_ok:
            raise InvalidCredentialsException()
        token = security.issue_token(
            found.user.user_id, found.user.role.value, self._jwt_secret, self._clock.now(),
            self._jwt_lifetime_minutes,
        )
        _logger.info("login_succeeded", extra={"user_id": found.user.user_id})
        return LoginResult(token=token, user_id=found.user.user_id, role=found.user.role)

    def authenticate(self, token: str) -> domain.User:
        """Validate the bearer token, then load the CURRENT user row on every call.

        The role comes from users.role (never the token claim); unknown or deactivated users
        raise InvalidTokenError exactly like a bad token. Nothing is cached between requests.
        """
        claims = security.decode_token(token, self._jwt_secret, self._clock.now())
        if not 0 < claims.user_id <= _MAX_USER_ID:
            raise InvalidTokenError("invalid token")
        with self._uow.read() as session:
            user = users_repo.find_by_id(session, UserId(claims.user_id))
        if user is None or not user.active:
            raise InvalidTokenError("invalid token")
        return user

    def describe(self, user: domain.User) -> UserView:
        with self._uow.read() as session:
            return UserView(user=user, full_name=users_repo.find_full_name(session, user))
