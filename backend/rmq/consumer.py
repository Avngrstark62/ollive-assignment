import json

from config import settings
from rmq.connection import rabbitmq


async def start_inference_log_consumer(handler) -> None:
    channel = await rabbitmq.get_channel(settings.RABBITMQ_PREFETCH_COUNT)
    queue = await channel.declare_queue(
        settings.RABBITMQ_INFERENCE_QUEUE,
        durable=True,
    )

    async with queue.iterator() as queue_iter:
        async for raw_message in queue_iter:
            async with raw_message.process():
                message = json.loads(raw_message.body.decode())
                await handler(message)
