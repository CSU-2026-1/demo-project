from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, nullcontext
from typing import Any

import elasticapm
from elasticapm import Client


def make_worker_apm_client() -> Client | None:
    server_url = os.getenv("ELASTIC_APM_SERVER_URL")
    if not server_url:
        return None

    client = Client(
        {
            "SERVICE_NAME": os.getenv("ELASTIC_APM_SERVICE_NAME", "todo-worker"),
            "SERVER_URL": server_url,
            "ENVIRONMENT": os.getenv("ELASTIC_APM_ENVIRONMENT", "local"),
            "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", ""),
            "TRANSACTION_SAMPLE_RATE": float(
                os.getenv("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", "1.0")
            ),
        }
    )
    elasticapm.instrument()
    return client


@asynccontextmanager
async def apm_transaction(
    client: Client | None,
    transaction_type: str,
    name: str,
    traceparent: str | None = None,
) -> AsyncIterator[None]:
    if client is None:
        yield
        return

    parent = elasticapm.trace_parent_from_string(traceparent) if traceparent else None
    client.begin_transaction(transaction_type, trace_parent=parent)
    result = "success"
    try:
        yield
    except Exception:
        result = "error"
        client.capture_exception()
        raise
    finally:
        client.end_transaction(name, result)


def capture_span(name: str, span_type: str) -> Any:
    if not elasticapm.get_trace_parent_header():
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
