from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import UUID, uuid4

from ingestion_service import ingest_inference_log


@dataclass
class InferenceResult:
    output_text: str


class InferenceCallError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def run_inference_with_logging(
    *,
    provider: str,
    model: str,
    conversation_id: UUID | str | None,
    invoke_provider: Callable[[], Any],
) -> InferenceResult:
    request_started_at = _utcnow()
    start_time = perf_counter()
    log_id = str(uuid4())
    conversation_id_value = str(conversation_id) if conversation_id is not None else None
    response: Any | None = None

    try:
        response = invoke_provider()
        output_text = _extract_output_text(provider, response)
        if not output_text:
            raise ValueError(f"{provider} returned an empty response.")

        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        ingest_inference_log(
            {
                "id": log_id,
                "request_started_at": request_started_at,
                "request_completed_at": request_completed_at,
                "provider": provider,
                "model": model,
                "latency_ms": latency_ms,
                "status": "success",
                "conversation_id": conversation_id_value,
                "response": response,
                "error": None,
            }
        )
        return InferenceResult(output_text=output_text.strip())
    except Exception as exc:
        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        ingest_inference_log(
            {
                "id": log_id,
                "request_started_at": request_started_at,
                "request_completed_at": request_completed_at,
                "provider": provider,
                "model": model,
                "latency_ms": latency_ms,
                "status": "error",
                "conversation_id": conversation_id_value,
                "response": response,
                "error": exc,
            }
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
