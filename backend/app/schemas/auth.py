from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    display_name: str | None = None
    profile_bio: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    full_name: str | None = Field(default=None, max_length=120)
    profile_bio: str | None = Field(default=None, max_length=500)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse
