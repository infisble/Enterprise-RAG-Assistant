from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "Enterprise RAG Assistant"
    api_secret_key: str = Field("change-me-in-production", alias="RAG_API_SECRET_KEY")
    access_token_minutes: int = Field(720, alias="RAG_ACCESS_TOKEN_MINUTES")
    cors_origins_raw: str = Field("http://localhost:5173", alias="RAG_CORS_ORIGINS")

    database_url: str = Field(
        "postgresql+psycopg2://rag:rag@postgres:5432/rag",
        alias="RAG_DATABASE_URL",
    )
    qdrant_url: str = Field("http://qdrant:6333", alias="RAG_QDRANT_URL")
    qdrant_collection: str = Field("enterprise_documents", alias="RAG_QDRANT_COLLECTION")
    embedding_dim: int = Field(384, alias="RAG_EMBEDDING_DIM")

    llm_provider: str = Field("mock", alias="RAG_LLM_PROVIDER")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_chat_model: str = Field("gpt-4o-mini", alias="RAG_OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", alias="RAG_OPENAI_EMBEDDING_MODEL")
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", alias="RAG_GEMINI_MODEL")
    gemini_embedding_model: str = Field("embedding-001", alias="RAG_GEMINI_EMBEDDING_MODEL")

    chunk_size: int = Field(900, alias="RAG_CHUNK_SIZE")
    chunk_overlap: int = Field(150, alias="RAG_CHUNK_OVERLAP")
    top_k: int = Field(5, alias="RAG_TOP_K")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
