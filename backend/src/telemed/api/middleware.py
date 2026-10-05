"""Request-id / correlation-id middleware, access log and last-resort error mapping."""
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from telemed.api.errors import unhandled_response
from telemed.service import bootstrap

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def resolve_request_id(incoming: str | None) -> str:
    """Echo a valid incoming id, otherwise generate a UUIDv4."""
    if incoming is not None and _VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return str(uuid.uuid4())


def _path_template(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) else "unmatched"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = bootstrap.bind_correlation_id(request_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:  # noqa: BLE001 - last-resort mapping, class only is logged
                bootstrap.log_event("unhandled_exception", error_class=type(exc).__name__)
                response = unhandled_response(exc)
            response.headers[REQUEST_ID_HEADER] = request_id
            bootstrap.log_event(
                "request_completed",
                method=request.method,
                path_template=_path_template(request),
                status_code=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return response
        finally:
            bootstrap.unbind_correlation_id(token)
