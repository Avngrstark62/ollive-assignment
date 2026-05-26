from datetime import datetime
from typing import Any
from uuid import UUID

from db import SessionLocal
from models import LLMInferenceLog


def ingest_inference_log(log: dict[str, Any]) -> None:
    validated_log = _validate_and_structure_log(log)

    inference_log = LLMInferenceLog(
        id=validated_log["id"],
        request_started_at=validated_log["request_started_at"],
        request_completed_at=validated_log["request_completed_at"],
        provider=validated_log["provider"],
        model=validated_log["model"],
        latency_ms=validated_log["latency_ms"],
        status=validated_log["status"],
        input_tokens=validated_log["input_tokens"],
        output_tokens=validated_log["output_tokens"],
        total_tokens=validated_log["total_tokens"],
        conversation_id=validated_log["conversation_id"],
        error_type=validated_log["error_type"],
        metadata_json=validated_log["metadata"],
    )

    db = SessionLocal()
    try:
        db.add(inference_log)
        db.commit()
    finally:
        db.close()


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    return UUID(value)


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _validate_and_structure_log(raw_log: dict[str, Any]) -> dict[str, Any]:
    _require_fields(
        raw_log,
        [
            "id",
            "request_started_at",
            "request_completed_at",
            "provider",
            "model",
            "latency_ms",
            "status",
        ],
    )

    provider = str(raw_log["provider"]).strip().lower()
    status = str(raw_log["status"]).strip().lower()
    if status not in {"success", "error"}:
        status = "error"

    response = raw_log.get("response")
    error = raw_log.get("error")

    input_tokens, output_tokens, total_tokens = _extract_usage(provider, response)
    error_type = _normalize_error_type(error) if error is not None else None
    metadata = _build_metadata(provider=provider, response=response, error=error)

    return {
        "id": UUID(str(raw_log["id"])),
        "request_started_at": _parse_datetime(raw_log["request_started_at"]),
        "request_completed_at": _parse_datetime(raw_log["request_completed_at"]),
        "provider": provider,
        "model": str(raw_log["model"]),
        "latency_ms": int(raw_log["latency_ms"]),
        "status": status,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "conversation_id": _parse_uuid(raw_log.get("conversation_id")),
        "error_type": error_type,
        "metadata": metadata,
    }


def _require_fields(raw_log: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if field not in raw_log or raw_log[field] is None]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required inference log fields: {missing_text}")


def _extract_usage(provider: str, response: Any | None) -> tuple[int | None, int | None, int | None]:
    if response is None:
        return None, None, None

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


def _normalize_error_type(error: Exception | None) -> str | None:
    if error is None:
        return None

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


def _build_metadata(provider: str, response: Any | None, error: Exception | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"provider": provider}

    if response is not None:
        provider_request_id = getattr(response, "id", None)
        if provider_request_id:
            metadata["provider_request_id"] = provider_request_id

    if error is not None:
        metadata["error_message"] = str(error)

    return metadata
