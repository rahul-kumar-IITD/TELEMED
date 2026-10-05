"""POST /api/auth/register and /api/auth/login (public)."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_auth_service
from telemed.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from telemed.service.auth_service import AuthService

router = APIRouter(prefix="/api/auth")


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> RegisterResponse:
    return RegisterResponse.from_domain(service.register(body.email, body.password, body.profile()))


@router.post("/login")
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    return LoginResponse.from_domain(service.login(body.email, body.password))
