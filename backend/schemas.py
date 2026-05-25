from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class MessagePairOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
