from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aio_pika
import redis.asyncio as redis
from aio_pika.abc import AbstractIncomingMessage
from openai import AsyncOpenAI
from sqlalchemy import func, select

from db import SessionLocal
from models import Todo, TodoStep
from tracing import (
    apm_transaction,
    capture_span,
    make_worker_apm_client,
    set_custom_context,
    set_labels,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://todo:todo@rabbitmq:5672/")
TODO_QUEUE_NAME = os.getenv("TODO_QUEUE_NAME", "todo.generate.steps")
WORKER_RETRY_DELAY_SECONDS = int(os.getenv("WORKER_RETRY_DELAY_SECONDS", "5"))
OPENAI_PROMPT_ID = os.getenv("OPENAI_PROMPT_ID", "fvtit6j69998ovg5jdnv")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TODO_CACHE_KEY_PREFIX = os.getenv("TODO_CACHE_KEY_PREFIX", "todo")

YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")

if not YANDEX_CLOUD_API_KEY:
    raise RuntimeError("YANDEX_CLOUD_API_KEY env var is required for worker")

client_kwargs: dict[str, Any] = {
    "api_key": YANDEX_CLOUD_API_KEY,
    "base_url": "https://ai.api.cloud.yandex.net/v1",
}
if YANDEX_CLOUD_FOLDER:
    client_kwargs["project"] = YANDEX_CLOUD_FOLDER
client = AsyncOpenAI(**client_kwargs)
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
apm_client = make_worker_apm_client()


def _todo_cache_key(todo_id: int) -> str:
    return f"{TODO_CACHE_KEY_PREFIX}:todo:{todo_id}"


def _todos_cache_key() -> str:
    return f"{TODO_CACHE_KEY_PREFIX}:todos:list"


async def invalidate_todo_cache(todo_id: int) -> None:
    try:
        set_labels(cache_invalidate=True, todo_id=todo_id)
        with capture_span("redis.invalidate_todo_cache", "cache"):
            deleted_count = await redis_client.delete(
                _todo_cache_key(todo_id),
                _todos_cache_key(),
            )
        set_labels(redis_deleted_keys=deleted_count)
    except Exception:
        set_labels(redis_invalidation_failed=True)
        logger.exception("Failed to invalidate cache for todo %s", todo_id)


async def llm_generate_steps(title: str) -> list[str]:
    logger.info("Calling LLM for title: %s", title)
    set_labels(
        llm_provider="yandex_cloud_openai_compatible",
        llm_prompt_id=OPENAI_PROMPT_ID,
        todo_title_length=len(title),
    )
    try:
        # Prompt text is stored in the model platform by Prompt ID.
        # For students: split a goal into 3-7 practical steps and return
        # strict JSON object {"steps":[...]} with no extra text.
        with capture_span("llm.responses.create", "external"):
            response = await client.responses.create(
                prompt={"id": OPENAI_PROMPT_ID},
                input=f"Goal: {title}",
            )
        with capture_span("llm.extract_output_text", "app"):
            content = (response.output_text or "").strip()
        set_labels(llm_output_chars=len(content))
        if not content:
            raise ValueError("Model output_text is empty")

        with capture_span("llm.parse_steps_json", "app"):
            payload = json.loads(content)
            raw_steps = payload["steps"]
            if not isinstance(raw_steps, list):
                raise ValueError("steps is not a list")

        with capture_span("llm.normalize_steps", "app"):
            steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        if not steps:
            raise ValueError("steps is empty")
        set_labels(llm_generated_steps=len(steps), llm_fallback_used=False)
        return steps
    except Exception as exc:
        set_labels(llm_fallback_used=True)
        logger.warning("LLM call failed for '%s': %s", title, exc)
        return [f"Break down requirements for: {title}"]


async def process_message(todo_id: int, title: str) -> None:
    set_labels(todo_id=todo_id, todo_title_length=len(title))
    async with SessionLocal() as db:
        with capture_span("worker.db.load_todo", "db"):
            todo = await db.get(Todo, todo_id)
        if not todo:
            set_labels(worker_skip_reason="todo_not_found")
            logger.warning("Todo %s not found, skip", todo_id)
            return

        with capture_span("worker.db.count_existing_steps", "db"):
            existing_steps_count = await db.scalar(
                select(func.count()).select_from(TodoStep).where(TodoStep.todo_id == todo_id)
            )
        set_labels(existing_steps_count=int(existing_steps_count or 0))
        if existing_steps_count and existing_steps_count > 0:
            set_labels(worker_skip_reason="steps_already_exist")
            logger.info("Todo %s already has %s steps, skip", todo_id, existing_steps_count)
            return

        target_title = title.strip() or todo.title
        set_labels(todo_target_title_length=len(target_title))
        with capture_span("worker.generate_steps", "app"):
            steps_texts = await llm_generate_steps(target_title)
        logger.info("Generated %d steps for todo %s", len(steps_texts), todo_id)

        with capture_span("worker.db.prepare_step_rows", "app"):
            saved_steps_count = 0
            max_step_length = 0
            for text in steps_texts:
                cleaned_text = text.strip()
                if not cleaned_text:
                    continue
                max_step_length = max(max_step_length, len(cleaned_text))
                db.add(
                    TodoStep(
                        todo_id=todo_id,
                        description=cleaned_text[:500],
                        completed=False,
                    )
                )
                saved_steps_count += 1

        set_labels(saved_steps_count=saved_steps_count, max_step_length=max_step_length)
        with capture_span("worker.db.commit_steps", "db"):
            await db.commit()
        with capture_span("worker.cache.invalidate_after_save", "cache"):
            await invalidate_todo_cache(todo_id)
        logger.info("Saved %d steps for todo %s", saved_steps_count, todo_id)


async def handle_message(message: AbstractIncomingMessage) -> None:
    traceparent = None
    if message.headers:
        traceparent_raw = message.headers.get("traceparent")
        if traceparent_raw:
            traceparent = str(traceparent_raw)

    async with apm_transaction(
        apm_client,
        "messaging",
        "RabbitMQ todo.generate.steps",
        traceparent=traceparent,
    ):
        set_labels(
            messaging_queue=TODO_QUEUE_NAME,
            messaging_body_bytes=len(message.body),
            traceparent_propagated=bool(traceparent),
        )
        set_custom_context(
            {
                "rabbitmq": {
                    "queue": TODO_QUEUE_NAME,
                    "body_bytes": len(message.body),
                    "content_type": message.content_type,
                    "delivery_tag": message.delivery_tag,
                    "redelivered": message.redelivered,
                    "traceparent_propagated": bool(traceparent),
                }
            }
        )
        try:
            with capture_span("message.decode_json", "app"):
                payload = json.loads(message.body.decode("utf-8"))
        except Exception:
            set_labels(message_invalid_json=True)
            logger.warning("Invalid JSON in message: %s", message.body)
            return

        with capture_span("message.validate_payload", "app"):
            todo_id_raw = payload.get("todo_id")
            if todo_id_raw is None:
                set_labels(message_invalid_reason="missing_todo_id")
                logger.warning("Message has no todo_id: %s", payload)
                return

            try:
                todo_id = int(todo_id_raw)
            except (TypeError, ValueError):
                set_labels(message_invalid_reason="invalid_todo_id")
                logger.warning("todo_id is not an integer: %s", payload)
                return

            title = str(payload.get("title", ""))
            set_labels(todo_id=todo_id, message_title_length=len(title))

        with capture_span("worker.process_message", "app"):
            await process_message(todo_id=todo_id, title=title)


async def consume_forever() -> None:
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue(TODO_QUEUE_NAME, durable=True)

                logger.info("Worker started. Waiting for messages from '%s'...", TODO_QUEUE_NAME)
                async with queue.iterator() as iterator:
                    async for message in iterator:
                        async with message.process(requeue=True):
                            await handle_message(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Worker loop crashed: %s. Retry in %s sec", exc, WORKER_RETRY_DELAY_SECONDS)
            await asyncio.sleep(WORKER_RETRY_DELAY_SECONDS)


async def _main() -> None:
    try:
        await consume_forever()
    finally:
        await redis_client.aclose()
        if apm_client:
            apm_client.close()


if __name__ == "__main__":
    asyncio.run(_main())
