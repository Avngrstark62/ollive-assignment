from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from rmq.constants import INFERENCE_LOG_EVENT
from rmq.publisher import publish_inference_log_event
from rmq.schemas import InferenceLogEvent


@dataclass
class InferenceResult:
    output_text: str


class InferenceCallError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


async def run_inference_with_logging(
    *,
    provider: str,
    model: str,
    conversation_id: UUID | str | None,
    invoke_provider: Callable[[], Awaitable[Any]],
) -> InferenceResult:
    request_started_at = _utcnow()
    start_time = perf_counter()
    log_id = str(uuid4())
    conversation_id_value = str(conversation_id) if conversation_id is not None else None
    response: Any | None = None

    try:
        response = await invoke_provider()
        output_text = _extract_output_text(provider, response)
        if not output_text:
            raise ValueError(f"{provider} returned an empty response.")

        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        await publish_inference_log_event(
            InferenceLogEvent(
                event_type=INFERENCE_LOG_EVENT,
                payload={
                    "id": log_id,
                    "request_started_at": request_started_at,
                    "request_completed_at": request_completed_at,
                    "provider": provider,
                    "model": model,
                    "latency_ms": latency_ms,
                    "status": "success",
                    "conversation_id": conversation_id_value,
                    "response": _serialize_response(response),
                    "error": None,
                },
            )
        )
        return InferenceResult(output_text=output_text.strip())
    except Exception as exc:
        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        await publish_inference_log_event(
            InferenceLogEvent(
                event_type=INFERENCE_LOG_EVENT,
                payload={
                    "id": log_id,
                    "request_started_at": request_started_at,
                    "request_completed_at": request_completed_at,
                    "provider": provider,
                    "model": model,
                    "latency_ms": latency_ms,
                    "status": "error",
                    "conversation_id": conversation_id_value,
                    "response": _serialize_response(response),
                    "error": str(exc),
                },
            )
        )
        raise InferenceCallError(str(exc)) from exc


def _extract_output_text(provider: str, response: Any) -> str:
    if provider == "openai":
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        return getattr(message, "content", "") or ""

    if provider == "anthropic":
        content = getattr(response, "content", None) or []
        if not content:
            return ""
        first_item = content[0]
        return getattr(first_item, "text", "") or ""

    raise ValueError(f"Unsupported provider: {provider}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_response(response: Any | None) -> dict[str, Any] | None:
    if response is None:
        return None
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)
    if isinstance(response, dict):
        return response
    return {"id": getattr(response, "id", None)}
