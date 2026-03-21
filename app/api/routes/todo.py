from fastapi import APIRouter, Depends, HTTPException, status
from dependency_injector.wiring import Provide, inject

from containers.container import Container
from schemas.todo import TodoCreate, TodoRead, TodoUpdate
from services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
@inject
async def create_todo(
    payload: TodoCreate,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    return await service.create(payload)


@router.get("/", response_model=list[TodoRead])
@inject
async def list_todos(
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> list[TodoRead]:
    return await service.list()


@router.get("/{todo_id}", response_model=TodoRead)
@inject
async def get_todo(
    todo_id: int,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    try:
        return await service.get(todo_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


@router.put("/{todo_id}", response_model=TodoRead)
@inject
async def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> TodoRead:
    try:
        return await service.update(todo_id, payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_todo(
    todo_id: int,
    service: TodoService = Depends(Provide[Container.todo_service]),
) -> None:
    try:
        await service.delete(todo_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
