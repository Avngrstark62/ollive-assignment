from openai import OpenAI

from config import settings
from models import Message

SYSTEM_PROMPT = "You are a concise and helpful assistant."

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_assistant_reply(messages: list[Message]) -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    chat_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_messages.extend(
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"}
    )

    response = get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=chat_messages,
    )

    reply = response.choices[0].message.content if response.choices else None
    if not reply:
        raise ValueError("OpenAI returned an empty response.")
    return reply.strip()
