from __future__ import annotations

import json
import logging
import os

import aio_pika
import elasticapm
from tracing import capture_span, set_custom_context, set_labels

logger = logging.getLogger(__name__)


class TodoEventPublisher:
    def __init__(self, amqp_url: str | None = None, queue_name: str | None = None) -> None:
        self.amqp_url = amqp_url or os.getenv("RABBITMQ_URL", "amqp://todo:todo@rabbitmq:5672/")
        self.queue_name = queue_name or os.getenv("TODO_QUEUE_NAME", "todo.generate.steps")
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        set_labels(messaging_queue=self.queue_name)
        with capture_span("rabbitmq.connect", "messaging"):
            self._connection = await aio_pika.connect_robust(self.amqp_url)
            self._channel = await self._connection.channel()
        with capture_span("rabbitmq.declare_queue", "messaging"):
            await self._channel.declare_queue(self.queue_name, durable=True)
        logger.info("RabbitMQ publisher connected to queue '%s'", self.queue_name)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ publisher connection closed")

    async def publish_todo_created(self, todo_id: int, title: str) -> None:
        if not self._connection or self._connection.is_closed or not self._channel:
            await self.connect()

        message_body = json.dumps(
            {"todo_id": todo_id, "title": title},
            ensure_ascii=False,
        ).encode("utf-8")

        message_headers = {}
        traceparent = elasticapm.get_trace_parent_header()
        if traceparent:
            message_headers["traceparent"] = traceparent

        set_labels(
            messaging_queue=self.queue_name,
            messaging_payload_bytes=len(message_body),
            todo_id=todo_id,
        )
        set_custom_context(
            {
                "messaging": {
                    "queue": self.queue_name,
                    "event": "todo.created",
                    "traceparent_propagated": bool(traceparent),
                }
            }
        )

        message = aio_pika.Message(
            body=message_body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers=message_headers,
        )

        assert self._channel is not None
        with capture_span("rabbitmq.publish todo.created", "messaging"):
            await self._channel.default_exchange.publish(message, routing_key=self.queue_name)
        logger.info("Published todo event: todo_id=%s", todo_id)
