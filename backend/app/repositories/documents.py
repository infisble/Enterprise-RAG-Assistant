from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Document, DocumentChunk, DocumentVisibility, User, UserRole


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_document(
        self,
        *,
        title: str,
        filename: str,
        content_type: str,
        visibility: DocumentVisibility,
        team_id: int | None,
        owner_id: int,
    ) -> Document:
        document = Document(
            title=title,
            filename=filename,
            content_type=content_type,
            visibility=visibility.value,
            team_id=team_id,
            owner_id=owner_id,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def add_chunk(self, *, document_id: int, chunk_index: int, text: str, point_id: str) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            qdrant_point_id=point_id,
        )
        self.db.add(chunk)
        return chunk

    def update_chunk_count(self, document: Document, chunk_count: int) -> Document:
        document.chunk_count = chunk_count
        self.db.add(document)
        self.db.flush()
        return document

    def visible_documents_query(self, user: User):
        if user.role == UserRole.admin.value:
            return select(Document).options(joinedload(Document.owner), joinedload(Document.team))
        return (
            select(Document)
            .options(joinedload(Document.owner), joinedload(Document.team))
            .where(
                or_(
                    Document.visibility == DocumentVisibility.public.value,
                    Document.owner_id == user.id,
                    (Document.visibility == DocumentVisibility.team.value) & (Document.team_id == user.team_id),
                )
            )
        )

    def list_visible(self, user: User) -> list[Document]:
        return list(self.db.scalars(self.visible_documents_query(user).order_by(Document.created_at.desc())))

    def visible_chunks_query(self, user: User):
        query = select(DocumentChunk).join(Document).options(joinedload(DocumentChunk.document))
        if user.role != UserRole.admin.value:
            query = query.where(
                or_(
                    Document.visibility == DocumentVisibility.public.value,
                    Document.owner_id == user.id,
                    (Document.visibility == DocumentVisibility.team.value) & (Document.team_id == user.team_id),
                )
            )
        return query

    def keyword_search(self, *, question: str, user: User, limit: int, metadata_filter: dict | None = None) -> list[DocumentChunk]:
        terms = [term.strip().lower() for term in question.split() if len(term.strip()) > 2]
        query = self.visible_chunks_query(user)
        if metadata_filter:
            query = self._apply_metadata_filter(query, metadata_filter)
        if terms:
            query = query.where(or_(*[DocumentChunk.text.ilike(f"%{term}%") for term in terms[:8]]))
        return list(self.db.scalars(query.limit(limit)))

    def get_visible_chunk(self, *, chunk_id: int, user: User) -> DocumentChunk | None:
        query = (
            select(DocumentChunk)
            .join(Document)
            .options(joinedload(DocumentChunk.document))
            .where(DocumentChunk.id == chunk_id)
        )
        if user.role != UserRole.admin.value:
            query = query.where(
                or_(
                    Document.visibility == DocumentVisibility.public.value,
                    Document.owner_id == user.id,
                    (Document.visibility == DocumentVisibility.team.value) & (Document.team_id == user.team_id),
                )
            )
        return self.db.scalar(query)

    def _apply_metadata_filter(self, query, metadata_filter: dict):
        if "visibility" in metadata_filter:
            query = query.where(Document.visibility == str(metadata_filter["visibility"]))
        if "team_id" in metadata_filter:
            query = query.where(Document.team_id == int(metadata_filter["team_id"]))
        if "document_id" in metadata_filter:
            query = query.where(Document.id == int(metadata_filter["document_id"]))
        return query
