from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import api_router
from containers.container import Container
from db import Base, engine, init_citus_for_todos_table

container = Container()
container.wire(packages=["api.routes"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_citus_for_todos_table()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Todo Clean Architecture Demo", lifespan=lifespan)
app.container = container  # type: ignore[attr-defined]
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
