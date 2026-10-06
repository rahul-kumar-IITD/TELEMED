"""Admin user management: list, deactivate (with safety rules) and reactivate."""
from sqlalchemy.orm import Session

from telemed.config.clock import Clock
from telemed.repository import appointments_repo, users_repo
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.domain import UserView
from telemed.types.enums import Role
from telemed.types.errors import (
    ActiveAppointmentsExistException,
    CannotDeactivateSelfException,
    NotFoundException,
)
from telemed.types.ids import UserId


class UserAdminService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def list_users(self, role: Role | None, active: bool | None) -> list[UserView]:
        with self._uow.read() as session:
            users = users_repo.list_users(session, role, active)
            return [UserView(u, users_repo.find_full_name(session, u)) for u in users]

    def deactivate(self, actor: domain.User, user_id: UserId) -> UserView:
        """Idempotent. Refuses self-deactivation and doctors with open appointments."""
        if actor.user_id == user_id:
            raise CannotDeactivateSelfException()
        with self._uow.transaction() as session:
            target = users_repo.find_by_id(session, user_id)
            if target is None:
                raise NotFoundException()
            if (
                target.role is Role.DOCTOR
                and appointments_repo.count_open_for_doctor(session, user_id) > 0
            ):
                raise ActiveAppointmentsExistException()
            users_repo.set_active(session, user_id, False, self._clock.now())
            return self._view(session, user_id)

    def reactivate(self, user_id: UserId) -> UserView:
        """Idempotent."""
        with self._uow.transaction() as session:
            if users_repo.find_by_id(session, user_id) is None:
                raise NotFoundException()
            users_repo.set_active(session, user_id, True, self._clock.now())
            return self._view(session, user_id)

    @staticmethod
    def _view(session: Session, user_id: UserId) -> UserView:
        user = users_repo.find_by_id(session, user_id)
        assert user is not None  # just verified inside this transaction
        return UserView(user, users_repo.find_full_name(session, user))
