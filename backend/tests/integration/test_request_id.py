"""E1-S2 AC2: X-Request-ID echoed when valid, replaced by a UUID otherwise."""
import uuid

import pytest
from fastapi.testclient import TestClient

from telemed.api.app import create_app
from telemed.api.middleware import resolve_request_id

H = "X-Request-ID"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _is_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


@pytest.mark.ac("AC-E1-S2-2")
@pytest.mark.parametrize(
    "value", ["11111111-1111-4111-8111-111111111111", "abc.DEF_123-x", "a", "a" * 64]
)
def test_valid_incoming_id_echoed(client: TestClient, value: str) -> None:
    assert client.get("/health", headers={H: value}).headers[H] == value


@pytest.mark.ac("AC-E1-S2-2")
@pytest.mark.parametrize("value", ["not a valid id!!", "a" * 65, "bad/slash", "unié"])
def test_invalid_incoming_id_replaced(client: TestClient, value: str) -> None:
    try:
        response = client.get("/health", headers={H: value})
    except UnicodeEncodeError:
        pytest.skip("client cannot encode this header")
    assert _is_uuid(response.headers[H])
    assert response.headers[H] != value


@pytest.mark.ac("AC-E1-S2-2")
def test_missing_id_generated(client: TestClient) -> None:
    first = client.get("/health").headers[H]
    second = client.get("/health").headers[H]
    assert _is_uuid(first) and _is_uuid(second) and first != second


@pytest.mark.ac("AC-E1-S2-2")
def test_header_on_error_responses(client: TestClient) -> None:
    assert H in client.get("/no-such-route").headers
    response = client.post("/health")
    assert response.status_code == 405
    assert H in response.headers
    assert response.headers["allow"] == "GET"


def test_resolve_rejects_trailing_newline() -> None:
    assert resolve_request_id("abc\n") != "abc\n"
    assert resolve_request_id(None) != ""
