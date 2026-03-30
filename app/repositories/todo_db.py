from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from models.todo import Todo, TodoStep
from repositories.base import BaseRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate


class PostgresTodoRepository(BaseRepository[Todo, TodoRead, TodoCreate, TodoUpdate]):
    model_cls = Todo
    read_schema = TodoRead

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory)

    async def create(self, data: TodoCreate) -> TodoRead:
        created = await super().create(data)
        return await self.get(created.id)

    async def get(self, item_id: int) -> TodoRead:
        async with self._session() as session:
            result = await session.execute(
                select(Todo).options(selectinload(Todo.steps)).where(Todo.id == item_id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            return self.read_schema.model_validate(obj)

    async def list(self) -> list[TodoRead]:
        async with self._session() as session:
            result = await session.execute(select(Todo).options(selectinload(Todo.steps)))
            objs = result.scalars().all()
            return [self.read_schema.model_validate(o) for o in objs]

    async def update(self, item_id: int, data: TodoUpdate) -> TodoRead:
        await super().update(item_id, data)
        return await self.get(item_id)

    async def delete(self, item_id: int) -> None:
        async with self._session() as session:
            obj = await session.get(Todo, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")

            await session.execute(delete(TodoStep).where(TodoStep.todo_id == item_id))
            await session.delete(obj)
            await session.commit()
