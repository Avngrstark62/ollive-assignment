import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db import SessionLocal, get_db
from inference_wrapper import InferenceCallError
from llm_service import generate_assistant_reply, stream_assistant_reply
from models import Conversation, Message
from schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
    MessagePairOut,
)

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
    stmt = (
        select(Conversation)
        .where(Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _get_active_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    conversation.title = _normalize_conversation_title(payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    conversation = _get_active_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    conversation.deleted_at = datetime.now(timezone.utc)
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conversation_id}/restore", response_model=ConversationOut)
def restore_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    conversation.deleted_at = None
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: UUID, db: Session = Depends(get_db)) -> list[Message]:
    conversation = _get_active_conversation(db, conversation_id)
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
) -> MessagePairOut:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content is required.")

    try:
        context_messages = await asyncio.to_thread(
            _build_context_messages_for_inference,
            conversation_id,
            content,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from exc

    try:
        inference_result = await generate_assistant_reply(
            context_messages,
            conversation_id=conversation_id,
            provider=payload.provider,
            model=payload.model,
        )
    except InferenceCallError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise _http_exception_for_value_error(exc) from exc

    assistant_text = inference_result.output_text.strip()
    if not assistant_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned an empty response.",
        )

    try:
        user_message, assistant_message = await asyncio.to_thread(
            _persist_turn,
            conversation_id,
            content,
            assistant_text,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from exc

    return MessagePairOut(user_message=user_message, assistant_message=assistant_message)


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
) -> StreamingResponse:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content is required.")

    try:
        context_messages = await asyncio.to_thread(
            _build_context_messages_for_inference,
            conversation_id,
            content,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from exc

    async def event_generator():
        assistant_chunks: list[str] = []
        try:
            async for chunk in stream_assistant_reply(
                context_messages,
                conversation_id=conversation_id,
                provider=payload.provider,
                model=payload.model,
            ):
                if await request.is_disconnected():
                    return
                assistant_chunks.append(chunk)
                yield _sse("token", {"text": chunk})
        except InferenceCallError as exc:
            yield _sse("error", {"detail": str(exc)})
            return
        except ValueError as exc:
            http_exc = _http_exception_for_value_error(exc)
            yield _sse("error", {"detail": http_exc.detail})
            return
        except Exception as exc:
            yield _sse("error", {"detail": str(exc)})
            return

        assistant_text = "".join(assistant_chunks).strip()
        if not assistant_text:
            yield _sse("error", {"detail": "Model returned an empty response."})
            return

        try:
            user_message, assistant_message = await asyncio.to_thread(
                _persist_turn,
                conversation_id,
                content,
                assistant_text,
            )
        except LookupError:
            yield _sse("error", {"detail": "Conversation not found."})
            return
        except Exception as exc:
            yield _sse("error", {"detail": f"Failed to persist messages: {exc}"})
            return

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


def _build_context_messages_for_inference(conversation_id: UUID, content: str) -> list[Message]:
    db = SessionLocal()
    try:
        conversation = _get_active_conversation(db, conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found.")

        context_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(settings.CONTEXT_WINDOW_MESSAGES)
        )
        context_messages = list(reversed(db.scalars(context_stmt).all()))
        context_messages.append(
            Message(
                conversation_id=conversation_id,
                role="user",
                content=content,
            )
        )
        return context_messages
    finally:
        db.close()


def _persist_turn(
    conversation_id: UUID,
    user_content: str,
    assistant_content: str,
) -> tuple[Message, Message]:
    db = SessionLocal()
    try:
        conversation = _get_active_conversation(db, conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found.")

        user_message = Message(conversation_id=conversation_id, role="user", content=user_content)
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        conversation.updated_at = datetime.now(timezone.utc)
        db.add(user_message)
        db.add(assistant_message)
        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        return user_message, assistant_message
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _http_exception_for_value_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    normalized = message.lower()
    if "not configured" in normalized:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _normalize_conversation_title(title: str | None) -> str | None:
    if title is None:
        return None
    normalized_title = title.strip()
    return normalized_title or None


def _get_active_conversation(db: Session, conversation_id: UUID) -> Conversation | None:
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.deleted_at.is_(None),
    )
    return db.scalar(stmt)
