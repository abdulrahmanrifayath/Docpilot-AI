from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=6, description="Plaintext password, minimum 6 characters")
    full_name: Optional[str] = Field(None, description="Optional full name or display name")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    email: str
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = Field(default=604800, description="Token validity duration in seconds (7 days)")


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
