from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from rmq.connection import rabbitmq
from router import router

app = FastAPI(title="Simple Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup_check_rabbitmq() -> None:
    channel = await rabbitmq.get_channel(settings.RABBITMQ_PREFETCH_COUNT)
    try:
        await channel.declare_queue(
            settings.RABBITMQ_INFERENCE_QUEUE,
            durable=True,
        )
    finally:
        await channel.close()


@app.on_event("shutdown")
async def shutdown_rabbitmq() -> None:
    await rabbitmq.close()
