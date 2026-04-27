from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from schemas.auth import AuthenticatedUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, username: str | None = None, role: str = "user") -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "role": role,
    }
    if username:
        payload["preferred_username"] = username
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role", "user")
    if role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contains unsupported role",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        subject=str(subject),
        username=payload.get("preferred_username") or payload.get("username"),
        role=role,
    )


def require_role(required_role: str):
    async def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' is required",
            )
        return current_user

    return dependency
