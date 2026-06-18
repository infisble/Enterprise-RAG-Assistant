import json
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import AuditLog, ChatMessage, ChatSession, Document, DocumentChunk, LLMRequest, User


class ObservabilityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_session(self, *, user: User, session_id: int | None, question: str) -> ChatSession:
        if session_id:
            session = self.db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
            if session:
                return session
        session = ChatSession(user_id=user.id, title=question[:80])
        self.db.add(session)
        self.db.flush()
        return session

    def add_message(
        self,
        *,
        session: ChatSession,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        session.updated_at = datetime.now(timezone.utc)
        message = ChatMessage(
            session_id=session.id,
            role=role,
            content=content,
            citations_json=json.dumps(citations or [], ensure_ascii=False) if citations is not None else None,
            latency_ms=latency_ms,
        )
        self.db.add(message)
        self.db.flush()
        return message

    def list_sessions(self, user: User) -> list[ChatSession]:
        return list(
            self.db.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == user.id)
                .options(selectinload(ChatSession.messages))
                .order_by(desc(ChatSession.updated_at))
            )
        )

    def log_llm_request(self, **values) -> LLMRequest:
        row = LLMRequest(**values)
        self.db.add(row)
        self.db.flush()
        return row

    def audit(self, **values) -> AuditLog:
        row = AuditLog(**values)
        self.db.add(row)
        self.db.flush()
        return row

    def metrics(self) -> dict:
        documents = self.db.scalar(select(func.count(Document.id))) or 0
        chunks = self.db.scalar(select(func.count(DocumentChunk.id))) or 0
        queries = self.db.scalar(select(func.count(LLMRequest.id))) or 0
        avg_latency = self.db.scalar(select(func.avg(LLMRequest.latency_ms))) or 0
        cost = self.db.scalar(select(func.coalesce(func.sum(LLMRequest.estimated_cost_usd), 0))) or 0
        failed = self.db.scalar(select(func.count(LLMRequest.id)).where(LLMRequest.status != "success")) or 0
        questions = list(
            self.db.scalars(
                select(ChatMessage.content)
                .where(ChatMessage.role == "user")
                .order_by(desc(ChatMessage.created_at))
                .limit(10)
            )
        )
        return {
            "documents": int(documents),
            "chunks": int(chunks),
            "queries": int(queries),
            "average_latency_ms": float(avg_latency),
            "estimated_cost_usd": float(cost),
            "top_questions": questions,
            "failed_answers": int(failed),
        }

    def llm_requests(self, limit: int = 100) -> list[LLMRequest]:
        return list(self.db.scalars(select(LLMRequest).order_by(desc(LLMRequest.created_at)).limit(limit)))

    def audit_logs(self, limit: int = 100) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)))
