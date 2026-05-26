from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, AsyncIterator, Awaitable, Callable
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


async def run_streaming_inference_with_logging(
    *,
    provider: str,
    model: str,
    conversation_id: UUID | str | None,
    invoke_provider_stream: Callable[[], Awaitable[Any]],
) -> AsyncIterator[str]:
    request_started_at = _utcnow()
    start_time = perf_counter()
    log_id = str(uuid4())
    conversation_id_value = str(conversation_id) if conversation_id is not None else None

    stream_response: Any | None = None
    response_id: str | None = None
    usage_payload: dict[str, Any] | None = None
    status = "success"
    error_message: str | None = None

    try:
        stream_response = await invoke_provider_stream()
        async for chunk in stream_response:
            if response_id is None:
                response_id = _extract_stream_response_id(provider, chunk)

            chunk_usage = _extract_stream_usage(provider, chunk)
            if chunk_usage is not None:
                usage_payload = chunk_usage

            text = _extract_stream_output_text(provider, chunk)
            if text:
                yield text
    except asyncio.CancelledError:
        status = "cancelled"
        error_message = "stream_cancelled"
        raise
    except Exception as exc:
        status = "error"
        error_message = str(exc)
        raise InferenceCallError(str(exc)) from exc
    finally:
        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        response_payload = {
            "id": response_id,
            "usage": usage_payload,
        }
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
                    "status": status,
                    "conversation_id": conversation_id_value,
                    "response": response_payload,
                    "error": error_message,
                },
            )
        )


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


def _serialize_usage(usage: Any | None) -> dict[str, Any] | None:
    if usage is None:
        return None
    model_dump = getattr(usage, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)
    if isinstance(usage, dict):
        return usage
    return None


def _extract_stream_output_text(provider: str, chunk: Any) -> str:
    if provider == "openai":
        choices = _read_value(chunk, "choices") or []
        if not choices:
            return ""
        first_choice = choices[0]
        delta = _read_value(first_choice, "delta")
        content = _read_value(delta, "content")
        return content or ""

    if provider == "anthropic":
        chunk_type = _read_value(chunk, "type")
        if chunk_type != "content_block_delta":
            return ""
        delta = _read_value(chunk, "delta")
        text = _read_value(delta, "text")
        return text or ""

    raise ValueError(f"Unsupported provider: {provider}")


def _extract_stream_usage(provider: str, chunk: Any) -> dict[str, Any] | None:
    if provider == "openai":
        return _serialize_usage(_read_value(chunk, "usage"))

    if provider == "anthropic":
        chunk_type = _read_value(chunk, "type")
        if chunk_type == "message_start":
            message = _read_value(chunk, "message")
            return _serialize_usage(_read_value(message, "usage"))
        if chunk_type == "message_delta":
            return _serialize_usage(_read_value(chunk, "usage"))
    return None


def _extract_stream_response_id(provider: str, chunk: Any) -> str | None:
    if provider == "openai":
        return _read_value(chunk, "id")
    if provider == "anthropic":
        chunk_type = _read_value(chunk, "type")
        if chunk_type == "message_start":
            message = _read_value(chunk, "message")
            return _read_value(message, "id")
        return _read_value(chunk, "id")
    return None


def _read_value(data: Any, key: str) -> Any:
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get(key)
    return getattr(data, key, None)
