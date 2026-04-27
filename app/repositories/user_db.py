from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.user import User
from schemas.auth import UserCreate, UserRead


class PostgresUserRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    def _session(self) -> AsyncSession:
        return self.session_factory()

    async def create(self, data: UserCreate, password_hash: str, role: str = "user") -> UserRead:
        async with self._session() as session:
            obj = User(username=data.username, password_hash=password_hash, role=role)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return UserRead.model_validate(obj)

    async def get_by_username(self, username: str) -> User | None:
        async with self._session() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()
