import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.utils import utcnow


# ---------- OTP ----------
def generate_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(email: str, code: str) -> str:
    """HMAC so a leaked DB does not reveal codes."""
    return hmac.new(
        settings.JWT_SECRET.encode(), f"{email}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def otp_matches(email: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(email, code), code_hash)


# ---------- JWT ----------
def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired token")
