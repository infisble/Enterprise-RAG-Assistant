from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_manager
from app.db.models import User
from app.repositories.observability import ObservabilityRepository
from app.schemas.admin import AuditLogRead, DashboardMetrics, LLMRequestRead

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(_: User = Depends(require_manager), db: Session = Depends(db_session)) -> DashboardMetrics:
    return DashboardMetrics(**ObservabilityRepository(db).metrics())


@router.get("/llm-requests", response_model=list[LLMRequestRead])
def llm_requests(_: User = Depends(require_manager), db: Session = Depends(db_session)) -> list[LLMRequestRead]:
    return ObservabilityRepository(db).llm_requests()


@router.get("/audit-logs", response_model=list[AuditLogRead])
def audit_logs(_: User = Depends(require_manager), db: Session = Depends(db_session)) -> list[AuditLogRead]:
    return ObservabilityRepository(db).audit_logs()
