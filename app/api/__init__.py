from fastapi import APIRouter

from api.routes import todo

api_router = APIRouter()
api_router.include_router(todo.router)
