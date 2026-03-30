from sqlalchemy import BigInteger, Boolean, Column, String
from sqlalchemy.orm import foreign, relationship

from db import Base


class TodoStep(Base):
    __tablename__ = "todo_steps"

    id = Column(BigInteger, primary_key=True, index=True)
    todo_id = Column(BigInteger, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)


class Todo(Base):
    __tablename__ = "todos"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(String(2000), nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    steps = relationship(
        "TodoStep",
        primaryjoin=lambda: Todo.id == foreign(TodoStep.todo_id),
        lazy="selectin",
        order_by=lambda: TodoStep.id,
        cascade="all, delete",
    )
