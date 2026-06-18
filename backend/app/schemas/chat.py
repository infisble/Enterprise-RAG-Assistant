from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=15)


class Citation(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    chunk_index: int
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    provider: str
