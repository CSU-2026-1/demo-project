from __future__ import annotations

from repositories.todo_db import PostgresTodoRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate
from services.base import BaseService


class TodoService(BaseService):
    """Business logic for todo items."""

    def __init__(self, repository: PostgresTodoRepository) -> None:
        super().__init__(repository)
        self.repository: PostgresTodoRepository

    async def create(self, data: TodoCreate) -> TodoRead:
        return await self.repository.create(data)

    async def get(self, todo_id: int) -> TodoRead:
        return await self.repository.get(todo_id)

    async def list(self) -> list[TodoRead]:
        return await self.repository.list()

    async def update(self, todo_id: int, data: TodoUpdate) -> TodoRead:
        return await self.repository.update(todo_id, data)

    async def delete(self, todo_id: int) -> None:
        await self.repository.delete(todo_id)
