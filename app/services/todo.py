from __future__ import annotations

import logging

from cache.decorators import cache_todo_get, cache_todos_list, invalidate_todo_cache
from cache.redis_cache import TodoCache
from messaging.rabbitmq import TodoEventPublisher
from repositories.todo_db import PostgresTodoRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate
from services.base import BaseService

logger = logging.getLogger(__name__)


class TodoService(BaseService):
    """Business logic for todo items."""

    def __init__(
        self,
        repository: PostgresTodoRepository,
        publisher: TodoEventPublisher,
        cache: TodoCache,
    ) -> None:
        super().__init__(repository)
        self.repository: PostgresTodoRepository
        self.publisher = publisher
        self.cache = cache

    @invalidate_todo_cache(lambda _args, _kwargs, result: result.id)
    async def create(self, data: TodoCreate) -> TodoRead:
        created = await self.repository.create(data)
        try:
            await self.publisher.publish_todo_created(todo_id=created.id, title=created.title)
        except Exception:
            logger.exception("Failed to publish todo.created event for todo %s", created.id)
        return created

    @cache_todo_get()
    async def get(self, todo_id: int) -> TodoRead:
        return await self.repository.get(todo_id)

    @cache_todos_list()
    async def list(self) -> list[TodoRead]:
        return await self.repository.list()

    @invalidate_todo_cache(
        lambda args, kwargs, _result: kwargs.get("todo_id") or (args[0] if args else None)
    )
    async def update(self, todo_id: int, data: TodoUpdate) -> TodoRead:
        return await self.repository.update(todo_id, data)

    @invalidate_todo_cache(
        lambda args, kwargs, _result: kwargs.get("todo_id") or (args[0] if args else None)
    )
    async def delete(self, todo_id: int) -> None:
        await self.repository.delete(todo_id)
