import json

import aio_pika

from config import settings
from rmq.connection import rabbitmq
from rmq.schemas import InferenceLogEvent


async def publish_inference_log_event(event: InferenceLogEvent) -> None:
    channel = await rabbitmq.get_channel(settings.RABBITMQ_PREFETCH_COUNT)

    try:
        await channel.declare_queue(
            settings.RABBITMQ_INFERENCE_QUEUE,
            durable=True,
        )

        message = aio_pika.Message(
            body=json.dumps(event.model_dump(), default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.RABBITMQ_INFERENCE_QUEUE,
        )
    finally:
        await channel.close()
