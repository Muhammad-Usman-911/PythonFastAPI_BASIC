from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import check_password_strength


class UserOut(BaseModel):
    """What the API returns for a user. hashed_password is NOT here, so it can never leak."""

    # from_attributes: build this from a SQLAlchemy object (user.email, user.id, ...)
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    role: str
    is_verified: bool
    has_password: bool = Field(description="False for users who only log in with email codes")
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


class ChangePasswordIn(BaseModel):
    current_password: str | None = Field(
        default=None, description="Required if the account already has a password"
    )
    new_password: str

    _strong = field_validator("new_password")(check_password_strength)
