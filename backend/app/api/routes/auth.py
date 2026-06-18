from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user, db_session, require_admin
from app.db.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead, UserUpdateRequest
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(db_session)) -> UserRead:
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> TokenResponse:
    return AuthService(db).login(payload)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)) -> UserRead:
    return AuthService._read_user(user)


@router.get("/users", response_model=list[UserRead])
def list_users(_: User = Depends(require_admin), db: Session = Depends(db_session)) -> list[UserRead]:
    return AuthService(db).list_users()


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(db_session),
) -> UserRead:
    return AuthService(db).update_user(user_id, payload)
