"""Domain exceptions with stable error codes."""


class DomainError(Exception):
    """Base class; `code` is the stable machine-readable identifier."""

    code = "INTERNAL_ERROR"


class SlotUnavailableException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "SLOT_UNAVAILABLE"


class InvalidAppointmentStateException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "INVALID_APPOINTMENT_STATE"


class EmailAlreadyRegisteredException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "EMAIL_ALREADY_REGISTERED"


class InvalidCredentialsException(DomainError):  # noqa: N818 - mirrors the other codes
    code = "INVALID_CREDENTIALS"


class NotFoundException(DomainError):  # noqa: N818 - mirrors the other codes
    """Object missing or not visible to the caller; the two cases are indistinguishable."""

    code = "NOT_FOUND"


class InvalidTokenError(Exception):
    """A bearer token is malformed, expired or not signed with our key."""
