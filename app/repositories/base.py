from __future__ import annotations

from typing import Generic, Iterable, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker


ModelT = TypeVar("ModelT")
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseRepository(Generic[ModelT, ReadSchemaT, CreateSchemaT, UpdateSchemaT]):
    """Generic CRUD implementation for SQLAlchemy models."""

    model_cls: Type[ModelT]
    read_schema: Type[ReadSchemaT]

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    def create(self, data: CreateSchemaT) -> ReadSchemaT:
        with self._session() as session:
            obj = self.model_cls(**data.model_dump())  # type: ignore[arg-type]
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return self.read_schema.model_validate(obj)

    def get(self, item_id: int) -> ReadSchemaT:
        with self._session() as session:
            obj = session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            return self.read_schema.model_validate(obj)

    def list(self) -> Iterable[ReadSchemaT]:
        with self._session() as session:
            objs = session.query(self.model_cls).all()
            return [self.read_schema.model_validate(o) for o in objs]

    def update(self, item_id: int, data: UpdateSchemaT) -> ReadSchemaT:
        with self._session() as session:
            obj = session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(obj, field, value)
            session.commit()
            session.refresh(obj)
            return self.read_schema.model_validate(obj)

    def delete(self, item_id: int) -> None:
        with self._session() as session:
            obj = session.get(self.model_cls, item_id)
            if not obj:
                raise KeyError(f"{self.model_cls.__name__} {item_id} not found")
            session.delete(obj)
            session.commit()
