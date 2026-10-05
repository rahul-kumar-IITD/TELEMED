"""Request/response models for /api/auth/*. No `role` field exists on the register request."""
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
)

from telemed.types.domain import LoginResult, ProfileData, User, UserView
from telemed.types.enums import Gender, Role

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Annotated[str, StringConstraints(max_length=254, pattern=_EMAIL_PATTERN)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class RegisterRequest(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)
    full_name: FullName
    age: int = Field(strict=True, ge=1, le=130)
    gender: Gender
    phone: Phone

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()

    def profile(self) -> ProfileData:
        return ProfileData(
            full_name=self.full_name, age=self.age, gender=self.gender, phone=self.phone
        )


class RegisterResponse(BaseModel):
    user_id: int
    role: Role
    email: str

    @classmethod
    def from_domain(cls, user: User) -> "RegisterResponse":
        return cls(user_id=user.user_id, role=user.role, email=user.email)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    expires_at: datetime
    user_id: int
    role: Role

    @field_serializer("expires_at")
    def _utc_z(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_domain(cls, result: LoginResult) -> "LoginResponse":
        return cls(
            access_token=result.token.access_token,
            token_type=result.token.token_type,
            expires_in=result.token.expires_in,
            expires_at=result.token.expires_at,
            user_id=result.user_id,
            role=result.role,
        )


class UserResponse(BaseModel):
    user_id: int
    email: str
    role: Role
    active: bool
    full_name: str | None
    created_at: datetime

    @field_serializer("created_at")
    def _utc_z(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_domain(cls, view: UserView) -> "UserResponse":
        user = view.user
        return cls(
            user_id=user.user_id, email=user.email, role=user.role, active=user.active,
            full_name=view.full_name, created_at=user.created_at,
        )
