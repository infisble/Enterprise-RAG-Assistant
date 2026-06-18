from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "qdrant_collection": settings.qdrant_collection,
    }
