from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import OtpRequest, OtpVerify, TokenOut, UserOut
from app.schemas.common import MessageOut
from app.services import auth_service, email_service, otp_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
def request_otp(
    data: OtpRequest, background: BackgroundTasks, db: Session = Depends(get_db)
):
    email = data.email.lower()
    code = otp_service.create_otp(db, email)
    # Sent after the response, so the request does not wait on SMTP.
    background.add_task(email_service.send_otp_email, email, code)
    return {"message": "If the email is valid, a code has been sent"}


@router.post("/verify-otp", response_model=TokenOut)
def verify_otp(data: OtpVerify, db: Session = Depends(get_db)):
    token = auth_service.login_with_otp(db, data.email.lower(), data.code)
    return {"access_token": token}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
