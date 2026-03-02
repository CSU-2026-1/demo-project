from dependency_injector import containers, providers

from db import SessionLocal, engine
from repositories.todo_db import PostgresTodoRepository
from services.todo import TodoService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["api.routes"])

    db_engine = providers.Object(engine)
    session_factory = providers.Object(SessionLocal)

    todo_repository = providers.Factory(PostgresTodoRepository, session_factory=session_factory)
    todo_service = providers.Factory(TodoService, repository=todo_repository)
