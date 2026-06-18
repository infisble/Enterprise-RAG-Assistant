from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User, UserRole
from app.db.session import get_db
from app.repositories.users import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(db_session)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    user = UserRepository(db).get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return user


def require_manager(user: User = Depends(current_user)) -> User:
    if user.role not in {UserRole.admin.value, UserRole.manager.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
