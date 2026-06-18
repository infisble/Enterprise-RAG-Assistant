import json
import re
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import get_request_id
from app.db.models import ChatSession, User
from app.repositories.documents import DocumentRepository
from app.repositories.observability import ObservabilityRepository
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_store import VectorStore


class RagService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.observability = ObservabilityRepository(db)
        self.embeddings = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm = LLMService()

    def chat(self, payload: ChatRequest, user: User) -> ChatResponse:
        started_at = time.perf_counter()
        session = self.observability.get_or_create_session(user=user, session_id=payload.session_id, question=payload.question)
        self.observability.add_message(session=session, role="user", content=payload.question)
        memory = self._memory(session)

        citations = self._retrieve(payload, user)
        grounded = bool(citations) and self._has_grounding(payload.question, citations)
        if not grounded:
            answer = self.llm.fallback_answer
            llm_result = self.llm.answer(payload.question, [], memory)
            llm_result.answer = answer
            llm_result.status = "grounding_failed"
        else:
            llm_result = self.llm.answer(payload.question, citations, memory)
            if not self._answer_is_grounded(llm_result.answer, citations):
                llm_result.answer = self.llm.fallback_answer
                llm_result.status = "grounding_failed"
                grounded = False

        latency_ms = round((time.perf_counter() - started_at) * 1000)
        citation_dicts = [citation.model_dump() for citation in citations] if grounded else []
        assistant_message = self.observability.add_message(
            session=session,
            role="assistant",
            content=llm_result.answer,
            citations=citation_dicts,
            latency_ms=latency_ms,
        )
        self.observability.log_llm_request(
            request_id=get_request_id() or "unknown",
            user_id=user.id,
            chat_session_id=session.id,
            provider=llm_result.provider,
            model=llm_result.model,
            prompt=llm_result.prompt,
            response=llm_result.answer,
            status=llm_result.status,
            error=llm_result.error,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=llm_result.total_tokens,
            estimated_cost_usd=llm_result.estimated_cost_usd,
            latency_ms=latency_ms,
        )
        self.observability.audit(
            request_id=get_request_id(),
            user_id=user.id,
            action="chat.ask",
            resource_type="chat_session",
            resource_id=str(session.id),
            status=llm_result.status,
            metadata_json=json.dumps({"citations": len(citation_dicts), "grounded": grounded}),
            latency_ms=latency_ms,
        )
        self.db.commit()

        return ChatResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            answer=llm_result.answer,
            citations=citations if grounded else [],
            provider=llm_result.provider,
            grounded=grounded,
            latency_ms=latency_ms,
            estimated_cost_usd=llm_result.estimated_cost_usd,
        )

    def _retrieve(self, payload: ChatRequest, user: User) -> list[Citation]:
        top_k = payload.top_k or settings.top_k
        vector = self.embeddings.embed([payload.question])[0]
        raw_vector = self.vector_store.search(vector, limit=top_k * 4)
        candidates: dict[int, dict] = {}

        for result in raw_vector:
            chunk_id = int(result.payload["chunk_id"])
            chunk = self.documents.get_visible_chunk(chunk_id=chunk_id, user=user)
            if not chunk or not self._metadata_matches(chunk, payload.metadata_filter):
                continue
            candidates[chunk_id] = {"chunk": chunk, "vector_score": float(result.score), "keyword_score": 0.0}

        keyword_chunks = self.documents.keyword_search(
            question=payload.question,
            user=user,
            limit=top_k * 4,
            metadata_filter=payload.metadata_filter,
        )
        question_terms = self._terms(payload.question)
        for chunk in keyword_chunks:
            keyword_score = self._keyword_score(question_terms, chunk.text)
            current = candidates.setdefault(chunk.id, {"chunk": chunk, "vector_score": 0.0, "keyword_score": 0.0})
            current["keyword_score"] = max(current["keyword_score"], keyword_score)

        reranked = sorted(
            candidates.values(),
            key=lambda item: (item["vector_score"] * 0.7) + (item["keyword_score"] * 0.3),
            reverse=True,
        )
        citations: list[Citation] = []
        for item in reranked[:top_k]:
            chunk = item["chunk"]
            score = (item["vector_score"] * 0.7) + (item["keyword_score"] * 0.3)
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    document_title=chunk.document.title,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    score=score,
                    vector_score=item["vector_score"],
                    keyword_score=item["keyword_score"],
                    text=chunk.text,
                )
            )
        return citations

    @staticmethod
    def _memory(session: ChatSession) -> list[str]:
        return [f"{message.role}: {message.content}" for message in session.messages[-6:]]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {term for term in re.findall(r"[a-zA-Zа-яА-Я0-9]{3,}", text.lower())}

    def _keyword_score(self, question_terms: set[str], text: str) -> float:
        if not question_terms:
            return 0.0
        text_terms = self._terms(text)
        return len(question_terms & text_terms) / len(question_terms)

    def _has_grounding(self, question: str, citations: list[Citation]) -> bool:
        question_terms = self._terms(question)
        return any(self._keyword_score(question_terms, citation.text) >= 0.12 for citation in citations)

    def _answer_is_grounded(self, answer: str, citations: list[Citation]) -> bool:
        if answer.strip() == self.llm.fallback_answer:
            return False
        if not citations:
            return False
        if "[" not in answer and self.llm_provider_is_real():
            return False
        return True

    @staticmethod
    def llm_provider_is_real() -> bool:
        return settings.llm_provider.lower() in {"openai", "gemini"}

    @staticmethod
    def _metadata_matches(chunk, metadata_filter: dict[str, str | int] | None) -> bool:
        if not metadata_filter:
            return True
        document = chunk.document
        if "visibility" in metadata_filter and document.visibility != str(metadata_filter["visibility"]):
            return False
        if "team_id" in metadata_filter and document.team_id != int(metadata_filter["team_id"]):
            return False
        if "document_id" in metadata_filter and document.id != int(metadata_filter["document_id"]):
            return False
        return True
