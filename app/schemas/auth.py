"""Request/response shapes for /auth. Node equivalent: DTOs / zod schemas.

FastAPI validates every request body against these classes. If validation fails,
your route never runs and the client gets a 422 `validation_error` envelope.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings

OTP_CODE = Field(pattern=r"^\d{6}$", examples=["123456"], description="6-digit code from the email")


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def check_password_strength(value: str) -> str:
    """Shared password rules (used by register, reset and change password)."""
    if len(value) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    if len(value.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes")  # bcrypt limit
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


class EmailIn(BaseModel):
    email: EmailStr = Field(examples=["dev@example.com"])

    _norm = field_validator("email")(_normalize_email)


class RegisterIn(EmailIn):
    password: str = Field(examples=["Passw0rd!"])
    full_name: str | None = Field(default=None, max_length=120, examples=["Ada Lovelace"])

    _strong = field_validator("password")(check_password_strength)


class LoginIn(EmailIn):
    password: str = Field(examples=["Passw0rd!"])


class CodeIn(EmailIn):
    code: str = OTP_CODE


class ResetPasswordIn(CodeIn):
    new_password: str = Field(examples=["N3wPassw0rd!"])

    _strong = field_validator("new_password")(check_password_strength)


class RefreshIn(BaseModel):
    refresh_token: str


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")
