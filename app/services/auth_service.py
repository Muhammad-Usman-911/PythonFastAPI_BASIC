from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User
from app.services import otp_service


def login_with_otp(db: Session, email: str, code: str) -> str:
    """Verify the OTP, create the user on first login, return a JWT."""
    otp_service.verify_otp(db, email, code)

    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # two parallel first logins
            db.rollback()
            user = db.scalar(select(User).where(User.email == email))
        else:
            db.refresh(user)

    return create_access_token(user.id)
