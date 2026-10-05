"""E1-S1 AC3: fee Decimal <-> integer minor units, no floats."""
import ast
from decimal import Decimal
from pathlib import Path

import pytest

from telemed.types.money import fee_from_string, from_minor, to_minor

SRC = Path(__file__).resolve().parents[2] / "src" / "telemed"


@pytest.mark.ac("AC-E1-S1-3")
def test_decimal_round_trip() -> None:
    assert to_minor(Decimal("500.00")) == 50000
    assert from_minor(50000) == Decimal("500.00")
    assert str(from_minor(50000)) == "500.00"


def test_to_minor_rejects_more_than_two_decimals() -> None:
    with pytest.raises(ValueError):
        to_minor(Decimal("1.001"))


def test_to_minor_rejects_negative() -> None:
    with pytest.raises(ValueError):
        to_minor(Decimal("-1.00"))


def test_to_minor_rejects_non_decimal() -> None:
    with pytest.raises(TypeError):
        to_minor(1.5)  # type: ignore[arg-type]


def test_from_minor_rejects_negative_and_non_int() -> None:
    with pytest.raises(ValueError):
        from_minor(-1)
    with pytest.raises(TypeError):
        from_minor(1.0)  # type: ignore[arg-type]


def test_fee_from_string() -> None:
    assert fee_from_string("500.00") == Decimal("500.00")
    for bad in ("500", "500.0", "-1.00", "abc", "1.001", "1e3"):
        with pytest.raises(ValueError):
            fee_from_string(bad)


@pytest.mark.ac("AC-E1-S1-3")
@pytest.mark.parametrize(
    "rel", ["types/money.py", "repository/mappers.py", "repository/models.py"]
)
def test_no_float_in_money_code_paths(rel: str) -> None:
    tree = ast.parse((SRC / rel).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {"float", "Float"}:
            raise AssertionError(f"{rel}:{node.lineno} uses {node.id}")
        if isinstance(node, ast.Attribute) and node.attr in {"Float", "REAL"}:
            raise AssertionError(f"{rel}:{node.lineno} uses {node.attr}")
