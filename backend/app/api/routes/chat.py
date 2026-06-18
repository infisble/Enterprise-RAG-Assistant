from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user, db_session
from app.db.models import User
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse, ChatSessionRead
from app.repositories.observability import ObservabilityRepository
from app.services.rag import RagService
import json

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> ChatResponse:
    return RagService(db).chat(payload, user)


@router.get("/history", response_model=list[ChatSessionRead])
def history(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[ChatSessionRead]:
    sessions = ObservabilityRepository(db).list_sessions(user)
    return [
        ChatSessionRead(
            id=session.id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            messages=[
                ChatMessageRead(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    citations=json.loads(message.citations_json or "[]"),
                    latency_ms=message.latency_ms,
                    created_at=message.created_at.isoformat(),
                )
                for message in session.messages
            ],
        )
        for session in sessions
    ]
