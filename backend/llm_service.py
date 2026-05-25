from uuid import UUID

from openai import OpenAI

from config import settings
from inference_wrapper import InferenceCallError, InferenceResult, run_inference_with_logging
from models import Message

SYSTEM_PROMPT = "You are a concise and helpful assistant."

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_assistant_reply(
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

    try:
        return run_inference_with_logging(
            provider="openai",
            model=settings.OPENAI_MODEL,
            conversation_id=conversation_id,
            invoke_provider=lambda: get_openai_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=chat_messages,
            ),
        )
    except InferenceCallError as exc:
        raise ValueError(str(exc)) from exc
