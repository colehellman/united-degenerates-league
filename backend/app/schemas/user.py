from pydantic import BaseModel, EmailStr, Field, UUID4, field_validator
from datetime import datetime
from typing import Optional
from app.models.user import UserRole, AccountStatus


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty123", "admin123", "letmein1", "welcome1", "monkey123",
    "abc12345", "iloveyou", "sunshine1", "princess1", "football1",
    "charlie1", "shadow12", "master12", "dragon12", "mustang1",
}


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("This password is too common. Please choose a stronger password")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID4
    role: UserRole
    status: AccountStatus
    created_at: datetime
    last_login_at: Optional[datetime] = None
    has_dismissed_onboarding: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    has_dismissed_onboarding: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("This password is too common. Please choose a stronger password")
        return v
