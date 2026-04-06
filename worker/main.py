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


def _todo_cache_key(todo_id: int) -> str:
    return f"{TODO_CACHE_KEY_PREFIX}:todo:{todo_id}"


def _todos_cache_key() -> str:
    return f"{TODO_CACHE_KEY_PREFIX}:todos:list"


async def invalidate_todo_cache(todo_id: int) -> None:
    try:
        await redis_client.delete(_todo_cache_key(todo_id), _todos_cache_key())
    except Exception:
        logger.exception("Failed to invalidate cache for todo %s", todo_id)


async def llm_generate_steps(title: str) -> list[str]:
    logger.info("Calling LLM for title: %s", title)
    try:
        # Prompt text is stored in the model platform by Prompt ID.
        # For students: split a goal into 3-7 practical steps and return
        # strict JSON object {"steps":[...]} with no extra text.
        response = await client.responses.create(
            prompt={"id": OPENAI_PROMPT_ID},
            input=f"Goal: {title}",
        )
        content = (response.output_text or "").strip()
        if not content:
            raise ValueError("Model output_text is empty")

        payload = json.loads(content)
        raw_steps = payload["steps"]
        if not isinstance(raw_steps, list):
            raise ValueError("steps is not a list")

        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        if not steps:
            raise ValueError("steps is empty")
        return steps
    except Exception as exc:
        logger.warning("LLM call failed for '%s': %s", title, exc)
        return [f"Break down requirements for: {title}"]


async def process_message(todo_id: int, title: str) -> None:
    async with SessionLocal() as db:
        todo = await db.get(Todo, todo_id)
        if not todo:
            logger.warning("Todo %s not found, skip", todo_id)
            return

        existing_steps_count = await db.scalar(
            select(func.count()).select_from(TodoStep).where(TodoStep.todo_id == todo_id)
        )
        if existing_steps_count and existing_steps_count > 0:
            logger.info("Todo %s already has %s steps, skip", todo_id, existing_steps_count)
            return

        target_title = title.strip() or todo.title
        steps_texts = await llm_generate_steps(target_title)
        logger.info("Generated %d steps for todo %s", len(steps_texts), todo_id)

        for text in steps_texts:
            cleaned_text = text.strip()
            if not cleaned_text:
                continue
            db.add(
                TodoStep(
                    todo_id=todo_id,
                    description=cleaned_text[:500],
                    completed=False,
                )
            )

        await db.commit()
        await invalidate_todo_cache(todo_id)
        logger.info("Saved %d steps for todo %s", len(steps_texts), todo_id)


async def handle_message(message: AbstractIncomingMessage) -> None:
    try:
        payload = json.loads(message.body.decode("utf-8"))
    except Exception:
        logger.warning("Invalid JSON in message: %s", message.body)
        return

    todo_id_raw = payload.get("todo_id")
    if todo_id_raw is None:
        logger.warning("Message has no todo_id: %s", payload)
        return

    try:
        todo_id = int(todo_id_raw)
    except (TypeError, ValueError):
        logger.warning("todo_id is not an integer: %s", payload)
        return

    title = str(payload.get("title", ""))
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


if __name__ == "__main__":
    asyncio.run(_main())
