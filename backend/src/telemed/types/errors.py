"""Domain exceptions with stable error codes."""


class DomainError(Exception):
    """Base class; `code` is the stable machine-readable identifier."""

    code = "INTERNAL_ERROR"


class SlotUnavailableException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "SLOT_UNAVAILABLE"


class InvalidAppointmentStateException(DomainError):  # noqa: N818 - name fixed by the BRD
    code = "INVALID_APPOINTMENT_STATE"
