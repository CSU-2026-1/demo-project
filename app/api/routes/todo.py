from fastapi import APIRouter, Depends, HTTPException, status
from dependency_injector.wiring import Provide, inject

from app.containers.container import Container
from app.schemas.todo import TodoCreate, TodoRead, TodoUpdate
from app.services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
@inject
def create_todo(
    payload: TodoCreate,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    return service.create(payload)


@router.get("/", response_model=list[TodoRead])
@inject
def list_todos(
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> list[TodoRead]:
    return service.list()


@router.get("/{todo_id}", response_model=TodoRead)
@inject
def get_todo(
    todo_id: int,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    try:
        return service.get(todo_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


@router.put("/{todo_id}", response_model=TodoRead)
@inject
def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    try:
        return service.update(todo_id, payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
def delete_todo(
    todo_id: int,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> None:
    try:
        service.delete(todo_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
