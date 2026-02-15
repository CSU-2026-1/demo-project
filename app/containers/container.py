from dependency_injector import containers, providers

from app.db import SessionLocal, engine
from app.repositories.todo_db import PostgresTodoRepository
from app.services.todo import TodoService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.api.routes"])

    db_engine = providers.Object(engine)
    session_factory = providers.Object(SessionLocal)

    todo_repository = providers.Factory(PostgresTodoRepository, session_factory=session_factory)
    todo_service = providers.Factory(TodoService, repository=todo_repository)
