"""Pure Decimal <-> integer minor-unit helpers (2 decimal places, no binary floats)."""
import re
from decimal import Decimal

_MINOR_FACTOR = Decimal(100)
_FEE_PATTERN = re.compile(r"^\d+\.\d{2}$")
_FEE_INPUT = re.compile(r"[0-9]{1,9}(\.[0-9]{1,2})?")


def to_minor(amount: Decimal) -> int:
    """Convert a non-negative Decimal with at most 2 decimals to integer minor units."""
    if not isinstance(amount, Decimal):
        raise TypeError("amount must be a Decimal")
    if amount < 0:
        raise ValueError("amount must not be negative")
    scaled = amount * _MINOR_FACTOR
    if scaled != scaled.to_integral_value():
        raise ValueError("amount has more than 2 decimal places")
    return int(scaled)


def from_minor(minor: int) -> Decimal:
    """Convert integer minor units to a Decimal with exactly 2 decimal places."""
    if isinstance(minor, bool) or not isinstance(minor, int):
        raise TypeError("minor units must be an int")
    if minor < 0:
        raise ValueError("minor units must not be negative")
    return (Decimal(minor) / _MINOR_FACTOR).quantize(Decimal("0.01"))


def fee_from_string(value: str) -> Decimal:
    """Parse an API fee string such as "500.00"."""
    if not _FEE_PATTERN.fullmatch(value):
        raise ValueError("fee must have exactly two decimal places")
    return Decimal(value)


def parse_fee(value: str) -> Decimal:
    """Parse a request fee: non-negative decimal, at most 2 decimal places (never a float)."""
    if not _FEE_INPUT.fullmatch(value):
        raise ValueError("fee must be a non-negative decimal with at most 2 decimal places")
    return Decimal(value)


def format_fee(amount: Decimal) -> str:
    """Serialise a fee as a 2-decimal string such as "500.00"."""
    return str(amount.quantize(Decimal("0.01")))
