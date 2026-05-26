from uuid import UUID

from openai import AsyncOpenAI
from collections.abc import AsyncIterator

from config import settings
from inference_wrapper import (
    InferenceCallError,
    InferenceResult,
    run_inference_with_logging,
    run_streaming_inference_with_logging,
)
from models import Message

SYSTEM_PROMPT = "You are a concise and helpful assistant."

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def generate_assistant_reply(
    messages: list[Message], *, conversation_id: UUID | None = None
) -> InferenceResult:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    chat_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_messages.extend(
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"}
    )

    async def invoke_provider():
        return await get_openai_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=chat_messages,
        )

    try:
        return await run_inference_with_logging(
            provider="openai",
            model=settings.OPENAI_MODEL,
            conversation_id=conversation_id,
            invoke_provider=invoke_provider,
        )
    except InferenceCallError as exc:
        raise ValueError(str(exc)) from exc


def stream_assistant_reply(
    messages: list[Message], *, conversation_id: UUID | None = None
) -> AsyncIterator[str]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    chat_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_messages.extend(
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"}
    )

    async def invoke_provider_stream():
        return await get_openai_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=chat_messages,
            stream=True,
            stream_options={"include_usage": True},
        )

    return run_streaming_inference_with_logging(
        provider="openai",
        model=settings.OPENAI_MODEL,
        conversation_id=conversation_id,
        invoke_provider_stream=invoke_provider_stream,
    )
