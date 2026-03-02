from fastapi import FastAPI

from api import api_router
from containers.container import Container
from db import Base, engine

Base.metadata.create_all(bind=engine)

container = Container()
container.wire(packages=["api.routes"])

app = FastAPI(title="Todo Clean Architecture Demo")
app.container = container  # type: ignore[attr-defined]
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
