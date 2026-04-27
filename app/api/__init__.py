from fastapi import APIRouter

from api.routes import auth, todo

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(todo.router)
