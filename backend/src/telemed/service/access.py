"""Ownership rules: wrong-owner and missing objects are indistinguishable (404)."""
from collections.abc import Collection

from telemed.types import domain
from telemed.types.enums import Role
from telemed.types.errors import NotFoundException
from telemed.types.ids import UserId


def ensure_can_read(actor: domain.User, owner_ids: Collection[UserId] | None) -> None:
    """Allow ADMIN (explicit bypass) or a listed owner; raise NotFoundException otherwise.

    `owner_ids` is None when the object does not exist, which is 404 even for ADMIN.
    """
    if owner_ids is None:
        raise NotFoundException()
    if actor.role is Role.ADMIN or actor.user_id in owner_ids:
        return
    raise NotFoundException()
