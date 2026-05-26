from typing import Any

from pydantic import BaseModel, Field


class InferenceLogEvent(BaseModel):
    event_type: str = Field(default="inference_log")
    payload: dict[str, Any]
