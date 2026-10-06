"""POST /api/auth/register and /login (public); GET /api/auth/me (any authenticated)."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_auth_service, get_current_user
from telemed.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from telemed.service.auth_service import AuthService
from telemed.types import domain

router = APIRouter(prefix="/api/auth")


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> RegisterResponse:
    return RegisterResponse.from_domain(service.register(body.email, body.password, body.profile()))


@router.post("/login")
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    return LoginResponse.from_domain(service.login(body.email, body.password))


@router.get("/me")
def me(
    user: domain.User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return UserResponse.from_domain(service.describe(user))
