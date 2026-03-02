from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from models.todo import Todo
from repositories.base import BaseRepository
from schemas.todo import TodoCreate, TodoRead, TodoUpdate


class PostgresTodoRepository(BaseRepository[Todo, TodoRead, TodoCreate, TodoUpdate]):
    model_cls = Todo
    read_schema = TodoRead

    def __init__(self, session_factory: sessionmaker) -> None:
        super().__init__(session_factory)
