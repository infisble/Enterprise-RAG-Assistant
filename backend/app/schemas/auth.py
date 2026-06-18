from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    team_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    team_id: int | None
    team_name: str | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    role: str | None = None
    team_name: str | None = Field(default=None, max_length=120)
