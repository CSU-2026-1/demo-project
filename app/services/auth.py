from __future__ import annotations

from repositories.user_db import PostgresUserRepository
from schemas.auth import Token, UserCreate, UserRead
from security import create_access_token, hash_password, verify_password
from tracing import capture_span, set_labels


class DuplicateUserError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class AuthService:
    def __init__(self, repository: PostgresUserRepository) -> None:
        self.repository = repository

    async def register(self, data: UserCreate) -> UserRead:
        set_labels(auth_flow="register", auth_role="user")
        return await self._register_with_role(data, role="user")

    async def register_admin(self, data: UserCreate) -> UserRead:
        set_labels(auth_flow="register", auth_role="admin")
        return await self._register_with_role(data, role="admin")

    async def _register_with_role(self, data: UserCreate, role: str) -> UserRead:
        set_labels(username_length=len(data.username), auth_role=role)
        with capture_span("auth.repository.get_by_username", "db"):
            existing = await self.repository.get_by_username(data.username)
        if existing:
            set_labels(auth_duplicate_user=True)
            raise DuplicateUserError("Username is already registered")
        with capture_span("auth.password.hash", "app"):
            password_hash = hash_password(data.password)
        with capture_span("auth.repository.create_user", "db"):
            created = await self.repository.create(data, password_hash, role=role)
        set_labels(user_id=created.id)
        return created

    async def authenticate(self, username: str, password: str) -> Token:
        set_labels(auth_flow="login", username_length=len(username))
        with capture_span("auth.repository.get_by_username", "db"):
            user = await self.repository.get_by_username(username)
        if not user or not user.is_active:
            set_labels(auth_success=False)
            raise InvalidCredentialsError("Invalid username or password")
        with capture_span("auth.password.verify", "app"):
            password_ok = verify_password(password, user.password_hash)
        if not password_ok:
            set_labels(auth_success=False, user_id=user.id, user_role=user.role)
            raise InvalidCredentialsError("Invalid username or password")
        with capture_span("auth.jwt.create", "app"):
            token = create_access_token(subject=str(user.id), username=user.username, role=user.role)
        set_labels(auth_success=True, user_id=user.id, user_role=user.role)
        return Token(access_token=token)
