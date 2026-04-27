from __future__ import annotations

from repositories.user_db import PostgresUserRepository
from schemas.auth import Token, UserCreate, UserRead
from security import create_access_token, hash_password, verify_password


class DuplicateUserError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class AuthService:
    def __init__(self, repository: PostgresUserRepository) -> None:
        self.repository = repository

    async def register(self, data: UserCreate) -> UserRead:
        return await self._register_with_role(data, role="user")

    async def register_admin(self, data: UserCreate) -> UserRead:
        return await self._register_with_role(data, role="admin")

    async def _register_with_role(self, data: UserCreate, role: str) -> UserRead:
        existing = await self.repository.get_by_username(data.username)
        if existing:
            raise DuplicateUserError("Username is already registered")
        return await self.repository.create(data, hash_password(data.password), role=role)

    async def authenticate(self, username: str, password: str) -> Token:
        user = await self.repository.get_by_username(username)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password")
        token = create_access_token(subject=str(user.id), username=user.username, role=user.role)
        return Token(access_token=token)
