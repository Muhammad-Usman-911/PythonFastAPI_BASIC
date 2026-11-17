"""Auth business rules. Routers call these; these call the DB and raise AppErrors.

Node equivalent: an `AuthService` class in NestJS / a `services/auth.js` in Express.

Functions that need to email a code RETURN the code; the router sends the email
in a background task. That keeps this file free of HTTP and easy to test.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.otp import OtpPurpose
from app.models.user import User
from app.schemas.auth import RegisterIn, TokensOut
from app.services import otp_service


# ---------- helpers ----------
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def issue_tokens(user: User) -> TokensOut:
    return TokensOut(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _ensure_active(user: User) -> None:
    if not user.is_active:
        raise ForbiddenError("This account is disabled", code="account_disabled")


# ---------- register + verify email ----------
def register(db: Session, data: RegisterIn) -> tuple[User, str]:
    """Create an unverified user. Returns (user, verification code to email)."""
    if get_user_by_email(db, data.email):
        raise ConflictError("An account with this email already exists", code="email_taken")

    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise ConflictError("An account with this email already exists", code="email_taken") from None
    db.refresh(user)

    code = otp_service.create_otp(db, user.email, OtpPurpose.VERIFY_EMAIL)
    return user, code


def resend_verification(db: Session, email: str) -> str | None:
    """Return a new code, or None when there is nothing to verify (unknown or verified email)."""
    user = get_user_by_email(db, email)
    if user is None or user.is_verified:
        return None  # same response either way: don't reveal which emails exist
    return otp_service.create_otp(db, email, OtpPurpose.VERIFY_EMAIL)


def verify_email(db: Session, email: str, code: str) -> tuple[User, TokensOut]:
    otp_service.verify_otp(db, email, OtpPurpose.VERIFY_EMAIL, code)
    user = get_user_by_email(db, email)
    if user is None:  # account deleted after the code was sent
        raise BadRequestError("Invalid or expired code", code="invalid_code")
    _ensure_active(user)
    user.is_verified = True
    db.commit()
    return user, issue_tokens(user)


# ---------- password login ----------
def login_with_password(db: Session, email: str, password: str) -> TokensOut:
    user = get_user_by_email(db, email)
    # Same error for "no such user" and "wrong password" (don't reveal which emails exist).
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password", code="invalid_credentials")
    _ensure_active(user)
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
        raise ForbiddenError("Please verify your email first", code="email_not_verified")
    return issue_tokens(user)


# ---------- passwordless (email code) login ----------
def request_login_code(db: Session, email: str) -> str:
    return otp_service.create_otp(db, email, OtpPurpose.LOGIN)


def login_with_code(db: Session, email: str, code: str) -> TokensOut:
    """Verify the code; create the user on first login (the code proves they own the email)."""
    otp_service.verify_otp(db, email, OtpPurpose.LOGIN, code)

    user = get_user_by_email(db, email)
    if user is None:
        user = User(email=email, is_verified=True)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # two parallel first logins
            db.rollback()
            user = get_user_by_email(db, email)
            assert user is not None
        else:
            db.refresh(user)
    elif not user.is_verified:
        user.is_verified = True
        db.commit()

    _ensure_active(user)
    return issue_tokens(user)


# ---------- refresh ----------
def refresh_tokens(db: Session, refresh_token: str) -> TokensOut:
    user_id = decode_token(refresh_token, "refresh")
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists", code="invalid_token")
    _ensure_active(user)
    return issue_tokens(user)


# ---------- forgot / reset password ----------
def forgot_password(db: Session, email: str) -> str | None:
    """Return a reset code, or None for unknown emails (the API answers the same either way)."""
    if get_user_by_email(db, email) is None:
        return None
    return otp_service.create_otp(db, email, OtpPurpose.RESET_PASSWORD)


def reset_password(db: Session, email: str, code: str, new_password: str) -> User:
    otp_service.verify_otp(db, email, OtpPurpose.RESET_PASSWORD, code)
    user = get_user_by_email(db, email)
    if user is None:
        raise BadRequestError("Invalid or expired code", code="invalid_code")
    user.hashed_password = hash_password(new_password)
    user.is_verified = True  # they just proved they own the email
    db.commit()
    return user
