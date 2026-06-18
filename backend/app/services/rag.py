from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.repositories.documents import DocumentRepository
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_store import VectorStore


class RagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.embeddings = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm = LLMService()

    def chat(self, payload: ChatRequest, user: User) -> ChatResponse:
        vector = self.embeddings.embed([payload.question])[0]
        raw_results = self.vector_store.search(vector, limit=(payload.top_k or settings.top_k) * 3)
        citations: list[Citation] = []
        seen: set[int] = set()
        for result in raw_results:
            chunk_id = int(result.payload["chunk_id"])
            if chunk_id in seen:
                continue
            chunk = self.documents.get_visible_chunk(chunk_id=chunk_id, user=user)
            if not chunk:
                continue
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    document_title=chunk.document.title,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    score=float(result.score),
                    text=chunk.text,
                )
            )
            seen.add(chunk_id)
            if len(citations) >= (payload.top_k or settings.top_k):
                break

        answer, provider = self.llm.answer(payload.question, citations)
        return ChatResponse(answer=answer, citations=citations, provider=provider)
