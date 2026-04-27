from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["user", "admin"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthenticatedUser(BaseModel):
    subject: str
    username: str | None = None
    role: UserRole = "user"
