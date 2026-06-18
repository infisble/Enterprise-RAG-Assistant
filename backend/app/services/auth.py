from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User, UserRole
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead, UserUpdateRequest


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: RegisterRequest) -> UserRead:
        if self.users.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

        team = self.users.get_or_create_team(payload.team_name) if payload.team_name else None
        user_count = self.db.scalar(select(func.count(User.id))) or 0
        role = UserRole.admin if user_count == 0 else UserRole.employee
        user = self.users.create(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            team=team,
            role=role,
        )
        self.db.commit()
        return self._read_user(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        token = create_access_token(
            subject=str(user.id),
            claims={"role": user.role, "team_id": user.team_id},
        )
        return TokenResponse(access_token=token)

    def list_users(self) -> list[UserRead]:
        return [self._read_user(user) for user in self.users.list()]

    def update_user(self, user_id: int, payload: UserUpdateRequest) -> UserRead:
        user = self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        try:
            role = UserRole(payload.role) if payload.role else None
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown role")
        team = self.users.get_or_create_team(payload.team_name) if payload.team_name else None
        updated = self.users.update_role_team(user, role=role, team=team)
        self.db.commit()
        return self._read_user(updated)

    @staticmethod
    def _read_user(user: User) -> UserRead:
        return UserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            team_id=user.team_id,
            team_name=user.team.name if user.team else None,
        )
