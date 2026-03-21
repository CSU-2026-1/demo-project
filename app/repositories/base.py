from __future__ import annotations

from typing import Generic, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


ModelT = TypeVar("ModelT")
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseRepository(Generic[ModelT, ReadSchemaT, CreateSchemaT, UpdateSchemaT]):
    """Generic CRUD implementation for SQLAlchemy models."""

    model_cls: Type[ModelT]
    read_schema: Type[ReadSchemaT]

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    def _session(self) -> AsyncSession:
        return self.session_factory()

    async def create(self, data: CreateSchemaT) -> ReadSchemaT:
        async with self._session() as session:
            obj = self.model_cls(**data.model_dump())  # type: ignore[arg-type]
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return self.read_schema.model_validate(obj)

    async def get(self, item_id: int) -> ReadSchemaT:
        async with self._session() as session:
            obj = await session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            return self.read_schema.model_validate(obj)

    async def list(self) -> list[ReadSchemaT]:
        async with self._session() as session:
            result = await session.execute(select(self.model_cls))
            objs = result.scalars().all()
            return [self.read_schema.model_validate(o) for o in objs]

    async def update(self, item_id: int, data: UpdateSchemaT) -> ReadSchemaT:
        async with self._session() as session:
            obj = await session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(obj, field, value)
            await session.commit()
            await session.refresh(obj)
            return self.read_schema.model_validate(obj)

    async def delete(self, item_id: int) -> None:
        async with self._session() as session:
            obj = await session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            await session.delete(obj)
            await session.commit()
