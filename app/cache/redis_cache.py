from __future__ import annotations

import json
import logging
import os

import redis.asyncio as redis

from schemas.todo import TodoRead

logger = logging.getLogger(__name__)


class TodoCache:
    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
        key_prefix: str | None = None,
    ) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.ttl_seconds = ttl_seconds or int(os.getenv("TODO_CACHE_TTL_SECONDS", "120"))
        self.key_prefix = key_prefix or os.getenv("TODO_CACHE_KEY_PREFIX", "todo")
        self._client: redis.Redis | None = None

    def _todo_key(self, todo_id: int) -> str:
        return f"{self.key_prefix}:todo:{todo_id}"

    def _todos_key(self) -> str:
        return f"{self.key_prefix}:todos:list"

    async def connect(self) -> None:
        if self._client is not None:
            return

        self._client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        await self._client.ping()
        logger.info("Redis cache connected")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis cache closed")

    async def _get_client(self) -> redis.Redis | None:
        if self._client is None:
            try:
                await self.connect()
            except Exception:
                logger.exception("Redis is not available")
                return None
        return self._client

    async def get_todo(self, todo_id: int) -> TodoRead | None:
        client = await self._get_client()
        if client is None:
            return None

        try:
            payload = await client.get(self._todo_key(todo_id))
            if not payload:
                return None
            return TodoRead.model_validate_json(payload)
        except Exception:
            logger.exception("Failed to read todo %s from cache", todo_id)
            return None

    async def set_todo(self, todo: TodoRead) -> None:
        client = await self._get_client()
        if client is None:
            return

        try:
            await client.set(self._todo_key(todo.id), todo.model_dump_json(), ex=self.ttl_seconds)
        except Exception:
            logger.exception("Failed to write todo %s to cache", todo.id)

    async def get_todos(self) -> list[TodoRead] | None:
        client = await self._get_client()
        if client is None:
            return None

        try:
            payload = await client.get(self._todos_key())
            if not payload:
                return None
            raw_items = json.loads(payload)
            return [TodoRead.model_validate(item) for item in raw_items]
        except Exception:
            logger.exception("Failed to read todos list from cache")
            return None

    async def set_todos(self, todos: list[TodoRead]) -> None:
        client = await self._get_client()
        if client is None:
            return

        try:
            payload = json.dumps(
                [todo.model_dump(mode="json") for todo in todos],
                ensure_ascii=False,
            )
            await client.set(self._todos_key(), payload, ex=self.ttl_seconds)
        except Exception:
            logger.exception("Failed to write todos list to cache")

    async def invalidate_todo(self, todo_id: int) -> None:
        client = await self._get_client()
        if client is None:
            return

        try:
            await client.delete(self._todo_key(todo_id))
        except Exception:
            logger.exception("Failed to invalidate todo %s cache", todo_id)

    async def invalidate_todos(self) -> None:
        client = await self._get_client()
        if client is None:
            return

        try:
            await client.delete(self._todos_key())
        except Exception:
            logger.exception("Failed to invalidate todos list cache")

    async def invalidate_all(self, todo_id: int) -> None:
        await self.invalidate_todo(todo_id)
        await self.invalidate_todos()
