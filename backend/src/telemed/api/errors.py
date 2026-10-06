"""Exception -> flat {code, message[, errors]} response mapping."""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from telemed.service import bootstrap
from telemed.types.errors import (
    DomainError,
    EmailAlreadyRegisteredException,
    ForbiddenException,
    InputValidationException,
    InvalidAppointmentStateException,
    InvalidCredentialsException,
    InvalidSlotStateException,
    NotFoundException,
    SlotUnavailableException,
)

_DOMAIN: dict[type[DomainError], tuple[int, str]] = {
    SlotUnavailableException: (409, "That slot is no longer available."),
    InvalidAppointmentStateException: (409, "That change is not allowed for this appointment."),
    InvalidSlotStateException: (409, "That slot cannot change to the requested state."),
    EmailAlreadyRegisteredException: (409, "That email is already registered."),
    InvalidCredentialsException: (401, "Invalid email or password."),
    NotFoundException: (404, "Resource not found."),
    ForbiddenException: (403, "You do not have access to this resource."),
}
_HTTP_CODES = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}
_HTTP_MESSAGES = {
    401: "Authentication required.",
    403: "You do not have access to this resource.",
    404: "Resource not found.",
    405: "Method not allowed.",
}


def error_body(
    code: str, message: str, errors: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if errors is not None:
        body["errors"] = errors
    return body


def _field_path(loc: tuple[Any, ...]) -> str:
    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        elif part not in ("body", "query", "path"):
            path += f".{part}" if path else str(part)
    return path or "body"


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status, message = _DOMAIN.get(type(exc), (500, "An unexpected error occurred."))
    return JSONResponse(error_body(exc.code, message), status_code=status)


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {"field": _field_path(tuple(item["loc"])), "message": str(item["msg"])}
        for item in exc.errors()
    ]
    return JSONResponse(
        error_body("VALIDATION_ERROR", "The request is invalid.", errors), status_code=422
    )


async def _input_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, InputValidationException)
    errors = [{"field": item.field, "message": item.message} for item in exc.errors]
    return JSONResponse(
        error_body("VALIDATION_ERROR", "The request is invalid.", errors), status_code=422
    )


async def _http_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status = exc.status_code
    code = _HTTP_CODES.get(status, "INTERNAL_ERROR")
    message = _HTTP_MESSAGES.get(status, "The request could not be processed.")
    return JSONResponse(error_body(code, message), status_code=status, headers=exc.headers)


def unhandled_response(exc: BaseException) -> JSONResponse:
    """Response for exceptions no handler claimed: 503 for SQLite lock timeouts, else 500."""
    if bootstrap.is_lock_timeout(exc):
        return JSONResponse(
            error_body("SERVICE_UNAVAILABLE", "The service is busy, please try again."),
            status_code=503,
        )
    return JSONResponse(
        error_body("INTERNAL_ERROR", "An unexpected error occurred."), status_code=500
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(InputValidationException, _input_validation_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
