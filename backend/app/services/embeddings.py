import hashlib
import math

import httpx

from app.core.config import settings


class EmbeddingService:
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        provider = settings.llm_provider.lower()
        if provider == "openai" and settings.openai_api_key:
            vectors = self._openai(texts)
        elif provider == "gemini" and settings.gemini_api_key:
            vectors = self._gemini(texts)
        else:
            vectors = [self._hash_embedding(text) for text in texts]
        return [self._fit_dimension(vector) for vector in vectors]

    def _openai(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_embedding_model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]

    def _gemini(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_embedding_model}:embedContent?key={settings.gemini_api_key}"
        )
        for text in texts:
            response = httpx.post(
                endpoint,
                json={"content": {"parts": [{"text": text}]}},
                timeout=60,
            )
            response.raise_for_status()
            vectors.append(response.json()["embedding"]["values"])
        return vectors

    @staticmethod
    def _hash_embedding(text: str) -> list[float]:
        values = [0.0] * settings.embedding_dim
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % settings.embedding_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    @staticmethod
    def _fit_dimension(vector: list[float]) -> list[float]:
        if len(vector) == settings.embedding_dim:
            return vector
        if len(vector) > settings.embedding_dim:
            return vector[: settings.embedding_dim]
        return vector + [0.0] * (settings.embedding_dim - len(vector))
