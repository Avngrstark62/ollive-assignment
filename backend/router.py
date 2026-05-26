import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db import get_db
from llm_service import generate_assistant_reply, stream_assistant_reply
from models import Conversation, Message
from schemas import ConversationCreate, ConversationOut, MessageCreate, MessageOut, MessagePairOut

router = APIRouter()


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> Conversation:
    conversation = Conversation(title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: UUID, db: Session = Depends(get_db)) -> list[Message]:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.scalars(stmt).all())


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePairOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
) -> MessagePairOut:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=payload.content.strip(),
    )
    if not user_message.content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content is required.")

    db.add(user_message)
    db.flush()

    context_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.CONTEXT_WINDOW_MESSAGES)
    )
    context_messages = list(reversed(db.scalars(context_stmt).all()))

    try:
        inference_result = await generate_assistant_reply(
            context_messages,
            conversation_id=conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=inference_result.output_text,
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return MessagePairOut(user_message=user_message, assistant_message=assistant_message)


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content is required.")

    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    context_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.CONTEXT_WINDOW_MESSAGES)
    )
    context_messages = list(reversed(db.scalars(context_stmt).all()))

    async def event_generator():
        assistant_chunks: list[str] = []
        try:
            async for chunk in stream_assistant_reply(
                context_messages,
                conversation_id=conversation_id,
            ):
                if await request.is_disconnected():
                    break
                assistant_chunks.append(chunk)
                yield _sse("token", {"text": chunk})
        except Exception as exc:
            yield _sse("error", {"detail": str(exc)})
            return

        assistant_text = "".join(assistant_chunks).strip()
        if not assistant_text:
            yield _sse("error", {"detail": "OpenAI returned an empty response."})
            return

        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_text,
        )
        conversation.updated_at = datetime.now(timezone.utc)
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        yield _sse(
            "done",
            {
                "user_message": MessageOut.model_validate(user_message).model_dump(mode="json"),
                "assistant_message": MessageOut.model_validate(assistant_message).model_dump(mode="json"),
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
