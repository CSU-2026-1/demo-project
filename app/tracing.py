from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import Any

import elasticapm
from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import FastAPI, Request, Response


def capture_span(name: str, span_type: str = "custom") -> Any:
    if elasticapm.get_client() is None or not elasticapm.get_trace_parent_header():
        return nullcontext()
    return elasticapm.capture_span(name, span_type)


def set_labels(**labels: Any) -> None:
    if not elasticapm.get_trace_parent_header():
        return
    safe_labels = {key: value for key, value in labels.items() if value is not None}
    if safe_labels:
        elasticapm.label(**safe_labels)


def set_custom_context(context: dict[str, Any]) -> None:
    if not elasticapm.get_trace_parent_header():
        return
    elasticapm.set_custom_context(context)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def setup_tracing(app: FastAPI) -> None:
    server_url = os.getenv("ELASTIC_APM_SERVER_URL")
    if not server_url:
        return

    @app.middleware("http")
    async def enrich_apm_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        route_path = _route_path(request)

        set_labels(
            http_route=route_path,
            http_status_code=response.status_code,
            query_param_count=len(request.query_params),
        )
        set_custom_context(
            {
                "request_details": {
                    "route": route_path,
                    "path": request.url.path,
                    "method": request.method,
                    "query_param_names": sorted(request.query_params.keys()),
                    "client_host": request.client.host if request.client else None,
                }
            }
        )
        return response

    app.add_middleware(
        ElasticAPM,
        client=make_apm_client(
            {
                "SERVICE_NAME": os.getenv("ELASTIC_APM_SERVICE_NAME", "todo-api"),
                "SERVER_URL": server_url,
                "ENVIRONMENT": os.getenv("ELASTIC_APM_ENVIRONMENT", "local"),
                "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", ""),
                "TRANSACTION_SAMPLE_RATE": float(
                    os.getenv("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", "1.0")
                ),
            }
        ),
    )
