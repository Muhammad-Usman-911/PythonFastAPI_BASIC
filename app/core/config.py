"""All settings in one place, read from environment variables / the `.env` file.

Node equivalent: `dotenv` + a `config.ts` that reads `process.env` and validates it
(e.g. with zod). Here `pydantic-settings` does both: every field below is read from
the env var with the same name, converted to the right type, and validated at startup.
A missing required value (like JWT_SECRET) stops the app with a clear error.

Usage anywhere:  `from app.core.config import settings` → `settings.JWT_SECRET`
"""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---------- App ----------
    APP_NAME: str = "FastAPI Starter"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    API_PREFIX: str = "/api/v1"
    # Comma separated list of frontend origins allowed to call the API from a browser.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    # Used to build links inside emails (e.g. "open the app").
    FRONTEND_URL: str = "http://localhost:3000"

    # ---------- Database ----------
    # SQLite works out of the box. For Postgres use:
    # postgresql+psycopg://user:password@localhost:5432/dbname
    DATABASE_URL: str = "sqlite:///./app.db"

    # ---------- Auth / JWT ----------
    # Required. Generate one: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # When true, password login is refused until the email is verified.
    REQUIRE_EMAIL_VERIFICATION: bool = True
    PASSWORD_MIN_LENGTH: int = 8

    # ---------- One-time codes (OTP) ----------
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_SECONDS: int = 60

    # ---------- Email ----------
    # console = print emails in the terminal (default, nothing to set up)
    # smtp    = really send them (Gmail, Mailpit, SendGrid SMTP, SES SMTP, ...)
    # memory  = keep them in a list (used by the tests)
    EMAIL_BACKEND: Literal["console", "smtp", "memory"] = "console"
    EMAIL_FROM: str = "no-reply@example.com"
    EMAIL_FROM_NAME: str = "FastAPI Starter"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    # STARTTLS on port 587 (Gmail, most providers). Set false for Mailpit (port 1025).
    SMTP_STARTTLS: bool = True
    # Implicit TLS on port 465. Use either this or STARTTLS, not both.
    SMTP_SSL: bool = False

    @field_validator("JWT_SECRET")
    @classmethod
    def secret_long_enough(cls, value: str) -> str:
        # HS256 keys shorter than 32 bytes are weak (and PyJWT warns about them).
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()  # type: ignore[call-arg]  (values come from the environment)
