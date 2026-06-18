import httpx

from app.core.config import settings
from app.schemas.chat import Citation


class LLMService:
    def answer(self, question: str, citations: list[Citation]) -> tuple[str, str]:
        provider = settings.llm_provider.lower()
        if provider == "openai" and settings.openai_api_key:
            return self._openai(question, citations), "openai"
        if provider == "gemini" and settings.gemini_api_key:
            return self._gemini(question, citations), "gemini"
        return self._mock(question, citations), "mock"

    def _prompt(self, question: str, citations: list[Citation]) -> str:
        context = "\n\n".join(
            f"[{index}] {citation.document_title} chunk {citation.chunk_index}: {citation.text}"
            for index, citation in enumerate(citations, start=1)
        )
        return (
            "You are an enterprise RAG assistant. Answer only from the supplied context. "
            "If the context is insufficient, say so. Cite sources inline as [1], [2].\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )

    def _openai(self, question: str, citations: list[Citation]) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "messages": [{"role": "user", "content": self._prompt(question, citations)}],
                "temperature": 0.2,
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _gemini(self, question: str, citations: list[Citation]) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        response = httpx.post(
            endpoint,
            json={"contents": [{"parts": [{"text": self._prompt(question, citations)}]}]},
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    @staticmethod
    def _mock(question: str, citations: list[Citation]) -> str:
        if not citations:
            return "I do not have enough accessible document context to answer this question."
        source_ids = ", ".join(f"[{index}]" for index in range(1, min(len(citations), 3) + 1))
        return (
            f"Based on the accessible document chunks, the answer to '{question}' is most likely covered "
            f"by the retrieved sources {source_ids}. Configure OpenAI or Gemini keys for production wording."
        )
