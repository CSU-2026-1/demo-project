from __future__ import annotations

import logging

from cache.decorators import cache_todo_get, cache_todos_list, invalidate_todo_cache
from cache.redis_cache import TodoCache
from messaging.rabbitmq import TodoEventPublisher
from repositories.todo_db import PostgresTodoRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate
from services.base import BaseService
from tracing import capture_span, set_labels

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
        set_labels(todo_title_length=len(data.title), todo_body_length=len(data.body))
        with capture_span("todo.repository.create", "db"):
            created = await self.repository.create(data)

        set_labels(todo_id=created.id, todo_done=created.done)
        with capture_span("todo.event.publish_created", "messaging"):
            try:
                await self.publisher.publish_todo_created(todo_id=created.id, title=created.title)
            except Exception:
                set_labels(todo_event_publish_failed=True)
                logger.exception("Failed to publish todo.created event for todo %s", created.id)
        return created

    @cache_todo_get()
    async def get(self, todo_id: int) -> TodoRead:
        set_labels(todo_id=todo_id)
        with capture_span("todo.repository.get", "db"):
            return await self.repository.get(todo_id)

    @cache_todos_list()
    async def list(self) -> list[TodoRead]:
        with capture_span("todo.repository.list", "db"):
            todos = await self.repository.list()
        set_labels(todo_count=len(todos))
        return todos

    @invalidate_todo_cache(
        lambda args, kwargs, _result: kwargs.get("todo_id") or (args[0] if args else None)
    )
    async def update(self, todo_id: int, data: TodoUpdate) -> TodoRead:
        set_labels(
            todo_id=todo_id,
            todo_update_title=data.title is not None,
            todo_update_body=data.body is not None,
            todo_update_done=data.done is not None,
        )
        with capture_span("todo.repository.update", "db"):
            return await self.repository.update(todo_id, data)

    @invalidate_todo_cache(
        lambda args, kwargs, _result: kwargs.get("todo_id") or (args[0] if args else None)
    )
    async def delete(self, todo_id: int) -> None:
        set_labels(todo_id=todo_id)
        with capture_span("todo.repository.delete", "db"):
            await self.repository.delete(todo_id)
