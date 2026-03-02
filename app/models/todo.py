from sqlalchemy import Boolean, Column, Integer, String

from db import Base


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(String(2000), nullable=False)
    done = Column(Boolean, default=False, nullable=False)
