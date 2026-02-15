from __future__ import annotations

from app.repositories.todo_db import PostgresTodoRepository
from app.schemas.todo import TodoCreate, TodoRead, TodoUpdate
from app.services.base import BaseService


class TodoService(BaseService):
    """Business logic for todo items."""

    def __init__(self, repository: PostgresTodoRepository) -> None:
        super().__init__(repository)
        self.repository: PostgresTodoRepository

    def create(self, data: TodoCreate) -> TodoRead:
        return self.repository.create(data)

    def get(self, todo_id: int) -> TodoRead:
        return self.repository.get(todo_id)

    def list(self) -> list[TodoRead]:
        return list(self.repository.list())

    def update(self, todo_id: int, data: TodoUpdate) -> TodoRead:
        return self.repository.update(todo_id, data)

    def delete(self, todo_id: int) -> None:
        self.repository.delete(todo_id)
