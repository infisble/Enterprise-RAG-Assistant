import uuid

from fastapi import HTTPException, UploadFile, status
from qdrant_client.http.models import PointStruct
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DocumentVisibility, User, UserRole
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentUploadForm, DocumentUploadResponse
from app.services.chunking import TextChunker
from app.services.embeddings import EmbeddingService
from app.services.parsing import DocumentParser
from app.services.vector_store import VectorStore


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.parser = DocumentParser()
        self.chunker = TextChunker(settings.chunk_size, settings.chunk_overlap)
        self.embeddings = EmbeddingService()
        self.vector_store = VectorStore()

    async def upload(self, *, file: UploadFile, form: DocumentUploadForm, user: User) -> DocumentUploadResponse:
        if form.visibility == DocumentVisibility.team and not (form.team_id or user.team_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team document requires team_id")
        if form.visibility == DocumentVisibility.public and user.role == UserRole.employee.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can publish public documents")

        text = await self.parser.parse(file)
        chunks = self.chunker.split(text)
        if not chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document has no extractable text")

        document = self.documents.create_document(
            title=form.title or file.filename or "Untitled document",
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            visibility=form.visibility,
            team_id=form.team_id if form.team_id is not None else user.team_id,
            owner_id=user.id,
        )

        vectors = self.embeddings.embed(chunks)
        points: list[PointStruct] = []
        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=True)):
            point_id = str(uuid.uuid4())
            chunk = self.documents.add_chunk(
                document_id=document.id,
                chunk_index=index,
                text=chunk_text,
                point_id=point_id,
            )
            self.db.flush()
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document.id,
                        "chunk_id": chunk.id,
                        "owner_id": user.id,
                        "team_id": document.team_id,
                        "visibility": document.visibility,
                        "title": document.title,
                    },
                )
            )

        self.vector_store.upsert(points)
        self.documents.update_chunk_count(document, len(chunks))
        self.db.commit()
        self.db.refresh(document)
        return DocumentUploadResponse(document=document, chunks_indexed=len(chunks))

    def list_visible(self, user: User):
        return self.documents.list_visible(user)
