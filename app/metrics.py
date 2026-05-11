import socket
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

INSTANCE = socket.gethostname()

REQUESTS_TOTAL = Counter(
    "todo_api_http_requests_total",
    "Total HTTP requests handled by this API replica.",
    ["instance", "method", "path", "status"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "todo_api_http_request_duration_seconds",
    "HTTP request duration in seconds for this API replica.",
    ["instance", "method", "path"],
)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def setup_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def collect_http_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            path = _route_path(request)
            REQUESTS_TOTAL.labels(
                instance=INSTANCE,
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()
            REQUEST_DURATION_SECONDS.labels(
                instance=INSTANCE,
                method=request.method,
                path=path,
            ).observe(time.perf_counter() - start)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
