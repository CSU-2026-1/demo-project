from fastapi import APIRouter

from app.api.routes import todo

api_router = APIRouter()
api_router.include_router(todo.router)
