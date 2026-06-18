import time

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.chat import Citation


class LLMResult(BaseModel):
    answer: str
    provider: str
    model: str | None
    prompt: str
    status: str = "success"
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0


class LLMService:
    fallback_answer = "I don't know based on provided documents."

    def answer(self, question: str, citations: list[Citation], memory: list[str] | None = None) -> LLMResult:
        provider = settings.llm_provider.lower()
        prompt = self._prompt(question, citations, memory or [])
        start = time.perf_counter()
        try:
            if provider == "openai" and settings.openai_api_key:
                answer, usage = self._openai(prompt)
                latency = round((time.perf_counter() - start) * 1000)
                return LLMResult(
                    answer=answer,
                    provider="openai",
                    model=settings.openai_chat_model,
                    prompt=prompt,
                    latency_ms=latency,
                    **usage,
                )
            if provider == "gemini" and settings.gemini_api_key:
                answer, usage = self._gemini(prompt)
                latency = round((time.perf_counter() - start) * 1000)
                return LLMResult(
                    answer=answer,
                    provider="gemini",
                    model=settings.gemini_model,
                    prompt=prompt,
                    latency_ms=latency,
                    **usage,
                )
            answer = self._mock(question, citations)
            latency = round((time.perf_counter() - start) * 1000)
            tokens = self._estimate_tokens(prompt + answer)
            return LLMResult(
                answer=answer,
                provider="mock",
                model="mock-grounded",
                prompt=prompt,
                latency_ms=latency,
                prompt_tokens=self._estimate_tokens(prompt),
                completion_tokens=self._estimate_tokens(answer),
                total_tokens=tokens,
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000)
            return LLMResult(
                answer=self.fallback_answer,
                provider=provider,
                model=None,
                prompt=prompt,
                status="error",
                error=str(exc),
                latency_ms=latency,
                prompt_tokens=self._estimate_tokens(prompt),
                total_tokens=self._estimate_tokens(prompt),
            )

    def _prompt(self, question: str, citations: list[Citation], memory: list[str]) -> str:
        context = "\n\n".join(
            f"[{index}] {citation.document_title} chunk {citation.chunk_index}: {citation.text}"
            for index, citation in enumerate(citations, start=1)
        )
        memory_text = "\n".join(memory[-6:])
        return (
            "You are an enterprise RAG assistant. Answer only from the supplied context. "
            "If the context is insufficient, answer exactly: I don't know based on provided documents. "
            "Every factual claim must be supported by inline citations like [1] or [2]. "
            "Do not use outside knowledge.\n\n"
            f"Conversation memory:\n{memory_text or 'No previous turns.'}\n\n"
            f"Question: {question}\n\nContext:\n{context or 'No accessible context.'}"
        )

    def _openai(self, prompt: str) -> tuple[str, dict]:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
        return payload["choices"][0]["message"]["content"], {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": self._estimate_openai_cost(prompt_tokens, completion_tokens),
        }

    def _gemini(self, prompt: str) -> tuple[str, dict]:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        response = httpx.post(
            endpoint,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["candidates"][0]["content"]["parts"][0]["text"]
        usage = payload.get("usageMetadata", {})
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        total_tokens = int(usage.get("totalTokenCount", prompt_tokens + completion_tokens))
        return answer, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": 0.0,
        }

    @staticmethod
    def _mock(question: str, citations: list[Citation]) -> str:
        if not citations:
            return LLMService.fallback_answer
        source_ids = ", ".join(f"[{index}]" for index in range(1, min(len(citations), 3) + 1))
        return f"Based on the provided documents, the answer is supported by sources {source_ids}."

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text.split()) * 4 // 3)

    @staticmethod
    def _estimate_openai_cost(prompt_tokens: int, completion_tokens: int) -> float:
        return round((prompt_tokens / 1_000_000 * 0.15) + (completion_tokens / 1_000_000 * 0.60), 6)
