from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError, UnauthorizedError
from app.core.security import generate_otp, hash_otp, otp_matches
from app.core.utils import as_utc, utcnow
from app.models.otp import OtpCode


def create_otp(db: Session, email: str) -> str:
    """Create a new OTP for the email and return the plain code (to be emailed)."""
    now = utcnow()

    last = db.scalar(
        select(OtpCode).where(OtpCode.email == email).order_by(OtpCode.id.desc()).limit(1)
    )
    if last and (now - as_utc(last.created_at)).total_seconds() < settings.OTP_RESEND_SECONDS:
        raise TooManyRequestsError("Please wait a moment before requesting another code")

    # Invalidate older codes
    db.execute(
        update(OtpCode).where(OtpCode.email == email, OtpCode.used.is_(False)).values(used=True)
    )

    code = generate_otp()
    db.add(
        OtpCode(
            email=email,
            code_hash=hash_otp(email, code),
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
    )
    db.commit()
    return code


def verify_otp(db: Session, email: str, code: str) -> None:
    """Raises UnauthorizedError unless the code is valid. Marks it used on success."""
    invalid = UnauthorizedError("Invalid or expired code")

    otp = db.scalar(
        select(OtpCode)
        .where(OtpCode.email == email, OtpCode.used.is_(False))
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    if not otp or as_utc(otp.expires_at) < utcnow():
        raise invalid

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp.used = True
        db.commit()
        raise invalid

    if not otp_matches(email, code, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise invalid

    otp.used = True
    db.commit()
