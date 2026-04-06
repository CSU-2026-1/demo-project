from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from schemas.todo import TodoRead

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def cache_todo_get() -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> TodoRead:
            todo_id_raw = kwargs.get("todo_id")
            if todo_id_raw is None and args:
                todo_id_raw = args[0]
            todo_id = int(todo_id_raw)

            cached = await self.cache.get_todo(todo_id)
            if cached is not None:
                return cached

            todo = await func(self, *args, **kwargs)
            await self.cache.set_todo(todo)
            return todo

        return wrapper  # type: ignore[return-value]

    return decorator


def cache_todos_list() -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> list[TodoRead]:
            cached = await self.cache.get_todos()
            if cached is not None:
                return cached

            todos = await func(self, *args, **kwargs)
            await self.cache.set_todos(todos)
            return todos

        return wrapper  # type: ignore[return-value]

    return decorator


def invalidate_todo_cache(
    todo_id_resolver: Callable[[tuple[Any, ...], dict[str, Any], Any], int | None],
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = await func(self, *args, **kwargs)
            todo_id = todo_id_resolver(args, kwargs, result)
            if todo_id is not None:
                await self.cache.invalidate_all(int(todo_id))
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
