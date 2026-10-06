"""Domain exceptions with stable error codes."""
from collections.abc import Sequence
from dataclasses import dataclass


class DomainError(Exception):
    """Base class; `code` is the stable machine-readable identifier."""

    code = "INTERNAL_ERROR"


class SlotUnavailableException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "SLOT_UNAVAILABLE"


class InvalidAppointmentStateException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "INVALID_APPOINTMENT_STATE"


class ChangeWindowClosedException(DomainError):  # noqa: N818 - mirrors the other codes
    """A patient cancel/reschedule less than 60 minutes before start, or after it."""

    code = "CHANGE_WINDOW_CLOSED"


class CannotDeactivateSelfException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "CANNOT_DEACTIVATE_SELF"


class ActiveAppointmentsExistException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "ACTIVE_APPOINTMENTS_EXIST"


class InvalidSlotStateException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "INVALID_SLOT_STATE"


class EmailAlreadyRegisteredException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "EMAIL_ALREADY_REGISTERED"


class InvalidCredentialsException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "INVALID_CREDENTIALS"


class NotFoundException(DomainError):  # noqa: N818 - mirrors the other codes
    """Object missing or not visible to the caller; the two cases are indistinguishable."""

    code = "NOT_FOUND"


class ForbiddenException(DomainError):  # noqa: N818 - mirrors the other codes
    """The actor's role or identity is not allowed to perform the operation."""

    code = "FORBIDDEN"


@dataclass(frozen=True)
class FieldError:
    """One field-level validation problem; `message` must never echo submitted values."""

    field: str
    message: str


class InputValidationException(DomainError):  # noqa: N818 - mirrors the other codes
    """Business-level input validation failure carrying field paths (422)."""

    code = "VALIDATION_ERROR"

    def __init__(self, errors: Sequence[FieldError]) -> None:
        super().__init__("input validation failed")
        self.errors = tuple(errors)


class InvalidTokenError(Exception):
    """A bearer token is malformed, expired or not signed with our key."""
