from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user, db_session
from app.db.models import DocumentVisibility, User
from app.schemas.documents import DocumentRead, DocumentUploadForm, DocumentUploadResponse
from app.services.documents import DocumentService

router = APIRouter()


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    visibility: DocumentVisibility = Form(default=DocumentVisibility.private),
    team_id: int | None = Form(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> DocumentUploadResponse:
    form = DocumentUploadForm(title=title, visibility=visibility, team_id=team_id)
    return await DocumentService(db).upload(file=file, form=form, user=user)


@router.get("", response_model=list[DocumentRead])
def list_documents(user: User = Depends(current_user), db: Session = Depends(db_session)) -> list[DocumentRead]:
    return DocumentService(db).list_visible(user)
