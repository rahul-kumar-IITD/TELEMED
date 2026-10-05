"""Patient registration and login."""
import logging

from telemed.config.clock import Clock
from telemed.repository import users_repo
from telemed.service import profile_service, security
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.domain import LoginResult, ProfileData
from telemed.types.enums import Role
from telemed.types.errors import EmailAlreadyRegisteredException, InvalidCredentialsException

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
