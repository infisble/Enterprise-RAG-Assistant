from datetime import datetime

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    documents: int
    chunks: int
    queries: int
    average_latency_ms: float
    estimated_cost_usd: float
    top_questions: list[str]
    failed_answers: int


class LLMRequestRead(BaseModel):
    id: int
    request_id: str
    provider: str
    model: str | None
    status: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogRead(BaseModel):
    id: int
    request_id: str | None
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    status: str
    metadata_json: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
