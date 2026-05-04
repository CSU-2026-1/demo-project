from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from api import api_router
from containers.container import Container
from db import Base, engine, init_citus_for_todos_table, init_users_table
from metrics import setup_metrics

logger = logging.getLogger(__name__)

container = Container()
container.wire(packages=["api.routes"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    publisher = container.rabbitmq_publisher()
    cache = container.redis_cache()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_users_table()
    await init_citus_for_todos_table()
    try:
        await publisher.connect()
    except Exception:
        logger.exception("RabbitMQ is not available on startup, will retry on publish")
    try:
        await cache.connect()
    except Exception:
        logger.exception("Redis is not available on startup, cache will be bypassed")

    try:
        yield
    finally:
        await cache.close()
        await publisher.close()
        await engine.dispose()


app = FastAPI(title="Todo Clean Architecture Demo", lifespan=lifespan)
app.container = container  # type: ignore[attr-defined]
setup_metrics(app)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
