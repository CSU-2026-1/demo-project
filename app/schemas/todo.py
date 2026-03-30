from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class TodoBase(BaseModel):
    title: str = Field(..., max_length=200)
    body: str = Field(..., max_length=2000)
    done: bool = False


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = Field(None, max_length=2000)
    done: Optional[bool] = None


class TodoStepRead(BaseModel):
    id: int
    description: str
    completed: bool

    model_config = ConfigDict(from_attributes=True)


class TodoRead(TodoBase):
    id: int
    steps: list[TodoStepRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
