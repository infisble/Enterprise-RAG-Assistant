from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=15)
    session_id: int | None = None
    metadata_filter: dict[str, str | int] | None = None


class Citation(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    chunk_index: int
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    text: str


class ChatResponse(BaseModel):
    session_id: int
    message_id: int | None = None
    answer: str
    citations: list[Citation]
    provider: str
    grounded: bool
    latency_ms: int
    estimated_cost_usd: float = 0.0


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    citations: list[Citation] = []
    latency_ms: int | None = None
    created_at: str


class ChatSessionRead(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageRead] = []
