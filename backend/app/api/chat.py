import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_ready_documents
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Chat, Document, Message, utcnow
from app.schemas.schemas import (
    ChatDetailOut,
    ChatRequest,
    ChatResponse,
    ChatSummaryOut,
    MessageOut,
)
from app.services import rag_service

router = APIRouter(prefix="/api", tags=["chat"])


def _summary(chat: Chat) -> dict:
    return {
        "id": chat.id,
        "title": chat.title,
        "document_ids": json.loads(chat.document_ids_json or "[]"),
        "message_count": len(chat.messages),
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
    }


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        sources=json.loads(m.sources_json) if m.sources_json else [],
        created_at=m.created_at,
    )


@router.post("/chat", response_model=ChatResponse)
def ask(req: ChatRequest, db: Session = Depends(get_db)):
    docs = get_ready_documents(db, req.document_ids) if req.document_ids else []

    chat = None
    history: List[dict] = []
    if req.chat_id:
        chat = db.get(Chat, req.chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        recent_messages = db.scalars(
            select(Message)
            .where(Message.chat_id == chat.id)
            .order_by(Message.id.desc())
            .limit(settings.history_messages)
        ).all()
        history = [
            {"role": message.role, "content": message.content}
            for message in reversed(recent_messages)
        ]

    has_any = db.scalar(select(Document.id).where(Document.processing_status == "ready").limit(1)) is not None
    doc_ids = [d.id for d in docs]
    result = rag_service.answer_question(req.question, doc_ids or None, history, has_any_documents=has_any)

    # Only save after the AI succeeded, so a failed request leaves no half-finished chat behind.
    if chat is None:
        chat = Chat(
            title=req.question[:60],
            document_id=doc_ids[0] if doc_ids else None,
            document_ids_json=json.dumps(doc_ids),
        )
        db.add(chat)
        db.flush()
    db.add(Message(chat_id=chat.id, role="user", content=req.question))
    db.add(
        Message(
            chat_id=chat.id,
            role="assistant",
            content=result["answer"],
            sources_json=json.dumps(result["sources"]),
        )
    )
    chat.updated_at = utcnow()
    db.commit()
    return ChatResponse(answer=result["answer"], chat_id=chat.id, sources=result["sources"], info=result["info"])


@router.get("/chats", response_model=List[ChatSummaryOut])
def list_chats(db: Session = Depends(get_db)):
    chats = db.scalars(select(Chat).order_by(Chat.updated_at.desc())).all()
    return [_summary(c) for c in chats]


@router.get("/chats/{chat_id}", response_model=ChatDetailOut)
def get_chat(chat_id: str, db: Session = Depends(get_db)):
    chat = db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    existing = set(db.scalars(select(Document.id)).all())
    data = _summary(chat)
    data["document_ids"] = [i for i in data["document_ids"] if i in existing]
    data["messages"] = [_message_out(m) for m in chat.messages]
    return data


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    chat = db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(chat)
    db.commit()
    return Response(status_code=204)
