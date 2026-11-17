"""Passwords, one-time codes and JWTs. Pure functions, no database.

Node equivalent: `bcrypt` + `jsonwebtoken` + `crypto`.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.utils import utcnow

TokenType = Literal["access", "refresh"]


# ---------- Passwords (bcrypt) ----------
# bcrypt only uses the first 72 bytes of a password; the schemas reject longer ones.
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:  # user created by OTP login has no password yet
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # malformed hash or > 72 bytes
        return False


# ---------- One-time codes ----------
def generate_otp() -> str:
    """A 6-digit code from a cryptographically secure source."""
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(email: str, purpose: str, code: str) -> str:
    """HMAC (keyed hash): a leaked database does not reveal usable codes."""
    message = f"{email}:{purpose}:{code}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), message, hashlib.sha256).hexdigest()


def otp_matches(email: str, purpose: str, code: str, code_hash: str) -> bool:
    # compare_digest takes the same time whatever the input (no timing attacks).
    return hmac.compare_digest(hash_otp(email, purpose, code), code_hash)


# ---------- JWT ----------
def create_token(user_id: int, token_type: TokenType) -> str:
    if token_type == "access":
        expires = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expires = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,  # stops a refresh token being used as an access token
        "iat": utcnow(),
        "exp": expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> int:
    """Return the user id inside a valid token, or raise 401."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired", code="token_expired") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token", code="invalid_token") from None

    if payload.get("type") != expected_type:
        raise UnauthorizedError(f"Expected an {expected_type} token", code="invalid_token")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid token", code="invalid_token") from None
