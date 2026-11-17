"""Create and check one-time email codes. Used by every code-based flow.

Rules (all configurable in .env):
- a code expires after OTP_EXPIRE_MINUTES
- OTP_MAX_ATTEMPTS wrong tries burn the code
- a code works once; asking for a new one cancels the old ones
- a new code can't be requested within OTP_RESEND_SECONDS (per email + purpose)
"""

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, TooManyRequestsError
from app.core.security import generate_otp, hash_otp, otp_matches
from app.core.utils import as_utc, utcnow
from app.models.otp import OtpCode, OtpPurpose


def create_otp(db: Session, email: str, purpose: OtpPurpose) -> str:
    """Store a new code for (email, purpose) and return the plain code to email."""
    now = utcnow()

    last = db.scalar(
        select(OtpCode)
        .where(OtpCode.email == email, OtpCode.purpose == purpose)
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    if last and (now - as_utc(last.created_at)).total_seconds() < settings.OTP_RESEND_SECONDS:
        raise TooManyRequestsError(
            "Please wait a moment before requesting another code",
            code="otp_cooldown",
            details={"retry_after_seconds": settings.OTP_RESEND_SECONDS},
        )

    # Cancel older unused codes for the same purpose.
    db.execute(
        update(OtpCode)
        .where(OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.used.is_(False))
        .values(used=True)
    )

    code = generate_otp()
    db.add(
        OtpCode(
            email=email,
            purpose=purpose,
            code_hash=hash_otp(email, purpose, code),
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
    )
    db.commit()
    return code


def verify_otp(db: Session, email: str, purpose: OtpPurpose, code: str) -> None:
    """Raise 400 `invalid_code` unless the code is valid. Marks it used on success."""
    invalid = BadRequestError("Invalid or expired code", code="invalid_code")

    otp = db.scalar(
        select(OtpCode)
        .where(OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.used.is_(False))
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    if otp is None or as_utc(otp.expires_at) < utcnow():
        raise invalid

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp.used = True
        db.commit()
        raise invalid

    if not otp_matches(email, purpose, code, otp.code_hash):
        otp.attempts += 1
        db.commit()  # commit the failed attempt even though we raise
        raise invalid

    otp.used = True
    db.commit()
