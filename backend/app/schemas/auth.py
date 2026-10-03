import uuid
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Frontend form label is "Full Name"; both `name` and `full_name` are accepted.
    name: str = Field(
        min_length=1, max_length=120, validation_alias=AliasChoices("name", "full_name"),
        examples=["Asha Verma"],
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    preferred_language: Literal["en", "hi"] = "en"

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    preferred_language: str
    created_at: datetime
