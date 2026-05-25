from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import UUID, uuid4

from ingestion_service import ingest_inference_log


@dataclass
class InferenceLog:
    id: str
    request_started_at: datetime
    request_completed_at: datetime
    provider: str
    model: str
    latency_ms: int
    status: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    conversation_id: str | None
    error_type: str | None
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InferenceResult:
    output_text: str
    log: InferenceLog


class InferenceCallError(Exception):
    def __init__(self, message: str, log: InferenceLog):
        super().__init__(message)
        self.log = log


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

    try:
        response = invoke_provider()
        output_text = _extract_output_text(provider, response)
        if not output_text:
            raise ValueError(f"{provider} returned an empty response.")

        input_tokens, output_tokens, total_tokens = _extract_usage(provider, response)
        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        metadata = _build_metadata(provider, response, error=None)

        log = InferenceLog(
            id=log_id,
            request_started_at=request_started_at,
            request_completed_at=request_completed_at,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            status="success",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            conversation_id=conversation_id_value,
            error_type=None,
            metadata=metadata,
        )
        ingest_inference_log(log.to_dict())
        return InferenceResult(output_text=output_text.strip(), log=log)
    except Exception as exc:
        request_completed_at = _utcnow()
        latency_ms = int((perf_counter() - start_time) * 1000)
        log = InferenceLog(
            id=log_id,
            request_started_at=request_started_at,
            request_completed_at=request_completed_at,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            status="error",
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            conversation_id=conversation_id_value,
            error_type=_normalize_error_type(exc),
            metadata=_build_metadata(provider, response=None, error=exc),
        )
        ingest_inference_log(log.to_dict())
        raise InferenceCallError(str(exc), log) from exc


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


def _extract_usage(provider: str, response: Any) -> tuple[int | None, int | None, int | None]:
    if provider == "openai":
        usage = getattr(response, "usage", None)
        if usage is None:
            return None, None, None
        input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return input_tokens, output_tokens, total_tokens

    if provider == "anthropic":
        usage = getattr(response, "usage", None)
        if usage is None:
            return None, None, None
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return input_tokens, output_tokens, total_tokens

    return None, None, None


def _build_metadata(provider: str, response: Any | None, error: Exception | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"provider": provider}

    if response is not None:
        request_id = getattr(response, "id", None)
        if request_id:
            metadata["provider_request_id"] = request_id

    if error is not None:
        metadata["error_message"] = str(error)

    return metadata


def _normalize_error_type(error: Exception) -> str:
    message = str(error).lower()
    if "rate limit" in message or "429" in message:
        return "rate_limit"
    if "timeout" in message:
        return "timeout"
    if "authentication" in message or "api key" in message or "401" in message:
        return "auth"
    if "invalid" in message or "400" in message:
        return "invalid_request"
    return "unknown"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
