from sqlalchemy import BigInteger, Boolean, Column, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Todo(Base):
    __tablename__ = "todos"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(200), nullable=False)


class TodoStep(Base):
    __tablename__ = "todo_steps"

    id = Column(BigInteger, primary_key=True, index=True)
    todo_id = Column(BigInteger, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
