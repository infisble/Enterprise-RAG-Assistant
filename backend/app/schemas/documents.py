from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import DocumentVisibility


class DocumentRead(BaseModel):
    id: int
    title: str
    filename: str
    content_type: str
    visibility: str
    team_id: int | None
    owner_id: int
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    chunks_indexed: int


class DocumentUploadForm(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    visibility: DocumentVisibility = DocumentVisibility.private
    team_id: int | None = None
