"""E6-S2 AC1: the domain-layer coverage threshold is configured and enforced."""
from tests.coverage_gate import domain_failure, load_domain_gate


def test_threshold_is_configured_at_95_for_the_types_package() -> None:
    minimum, include = load_domain_gate()
    assert minimum == 95.0
    assert include == ["*/telemed/types/*"]


def test_failure_message_only_below_threshold() -> None:
    assert domain_failure(94.99, 95.0) is not None
    assert "94.99" in (domain_failure(94.99, 95.0) or "")
    assert domain_failure(95.0, 95.0) is None
    assert domain_failure(100.0, 95.0) is None
