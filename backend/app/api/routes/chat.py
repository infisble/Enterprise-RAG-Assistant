from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user, db_session
from app.db.models import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import RagService

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(current_user), db: Session = Depends(db_session)) -> ChatResponse:
    return RagService(db).chat(payload, user)
