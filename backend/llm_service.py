from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from config import settings
from inference_wrapper import (
    InferenceCallError,
    InferenceResult,
    run_inference_with_logging,
    run_streaming_inference_with_logging,
)
from models import Message

SYSTEM_PROMPT = "You are a concise and helpful assistant."

_openai_client: AsyncOpenAI | None = None
_anthropic_client: AsyncAnthropic | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured.")
        _anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def _build_chat_messages(messages: list[Message]) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"}
    ]


def _resolve_model(provider: str, model: str | None) -> str:
    if model:
        return model
    if provider == "openai":
        return settings.OPENAI_MODEL
    if provider == "anthropic":
        return settings.ANTHROPIC_MODEL
    raise ValueError(f"Unsupported provider: {provider}")


def _validate_provider(provider: str) -> Literal["openai", "anthropic"]:
    normalized_provider = provider.strip().lower()
    if normalized_provider not in {"openai", "anthropic"}:
        raise ValueError("Unsupported provider. Supported providers: openai, anthropic.")
    return normalized_provider


async def generate_assistant_reply(
    messages: list[Message],
    *,
    conversation_id: UUID | None = None,
    provider: str = "openai",
    model: str | None = None,
) -> InferenceResult:
    resolved_provider = _validate_provider(provider)
    resolved_model = _resolve_model(resolved_provider, model)
    chat_messages = _build_chat_messages(messages)

    async def invoke_provider():
        if resolved_provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured.")
            return await get_openai_client().chat.completions.create(
                model=resolved_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *chat_messages],
            )

        return await get_anthropic_client().messages.create(
            model=resolved_model,
            system=SYSTEM_PROMPT,
            messages=chat_messages,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        )

    try:
        return await run_inference_with_logging(
            provider=resolved_provider,
            model=resolved_model,
            conversation_id=conversation_id,
            invoke_provider=invoke_provider,
        )
    except InferenceCallError as exc:
        raise ValueError(str(exc)) from exc


def stream_assistant_reply(
    messages: list[Message],
    *,
    conversation_id: UUID | None = None,
    provider: str = "openai",
    model: str | None = None,
) -> AsyncIterator[str]:
    resolved_provider = _validate_provider(provider)
    resolved_model = _resolve_model(resolved_provider, model)
    chat_messages = _build_chat_messages(messages)

    async def invoke_provider_stream():
        if resolved_provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured.")
            return await get_openai_client().chat.completions.create(
                model=resolved_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *chat_messages],
                stream=True,
                stream_options={"include_usage": True},
            )

        return await get_anthropic_client().messages.create(
            model=resolved_model,
            system=SYSTEM_PROMPT,
            messages=chat_messages,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            stream=True,
        )

    return run_streaming_inference_with_logging(
        provider=resolved_provider,
        model=resolved_model,
        conversation_id=conversation_id,
        invoke_provider_stream=invoke_provider_stream,
    )
