from __future__ import annotations

import logging

from messaging.rabbitmq import TodoEventPublisher
from repositories.todo_db import PostgresTodoRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate
from services.base import BaseService

logger = logging.getLogger(__name__)


class TodoService(BaseService):
    """Business logic for todo items."""

    def __init__(self, repository: PostgresTodoRepository, publisher: TodoEventPublisher) -> None:
        super().__init__(repository)
        self.repository: PostgresTodoRepository
        self.publisher = publisher

    async def create(self, data: TodoCreate) -> TodoRead:
        created = await self.repository.create(data)
        try:
            await self.publisher.publish_todo_created(todo_id=created.id, title=created.title)
        except Exception:
            logger.exception("Failed to publish todo.created event for todo %s", created.id)
        return created

    async def get(self, todo_id: int) -> TodoRead:
        return await self.repository.get(todo_id)

    async def list(self) -> list[TodoRead]:
        return await self.repository.list()

    async def update(self, todo_id: int, data: TodoUpdate) -> TodoRead:
        return await self.repository.update(todo_id, data)

    async def delete(self, todo_id: int) -> None:
        await self.repository.delete(todo_id)
