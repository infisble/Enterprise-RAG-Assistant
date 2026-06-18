from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Team, User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def list(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.created_at.desc())))

    def get_or_create_team(self, name: str) -> Team:
        normalized = name.strip()
        team = self.db.scalar(select(Team).where(Team.name == normalized))
        if team:
            return team
        team = Team(name=normalized)
        self.db.add(team)
        self.db.flush()
        return team

    def create(
        self,
        *,
        email: str,
        full_name: str,
        hashed_password: str,
        team: Team | None,
        role: UserRole = UserRole.employee,
    ) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            hashed_password=hashed_password,
            team_id=team.id if team else None,
            role=role.value,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update_role_team(self, user: User, *, role: UserRole | None, team: Team | None) -> User:
        if role:
            user.role = role.value
        if team:
            user.team_id = team.id
        self.db.add(user)
        self.db.flush()
        return user
