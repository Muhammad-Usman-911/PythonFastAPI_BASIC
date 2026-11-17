"""/auth endpoints. Routers only do HTTP: read input, call a service, wrap the result.

Node equivalent: an Express `Router()` / a NestJS `@Controller('auth')`.
"""

from fastapi import APIRouter, BackgroundTasks, status

from app.core.responses import ERROR_RESPONSES, ApiResponse, ok
from app.deps import DbSession
from app.schemas.auth import CodeIn, EmailIn, LoginIn, RefreshIn, RegisterIn, ResetPasswordIn, TokensOut
from app.schemas.user import UserOut
from app.services import auth_service, email_service

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)

# Same message whether or not the email exists, so attackers can't probe for accounts.
CODE_SENT = "If the email can receive one, a code has been sent"


@router.post("/register", response_model=ApiResponse[UserOut], status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: DbSession, background: BackgroundTasks):
    """Create an account with email + password. A 6-digit verification code is emailed."""
    user, code = auth_service.register(db, data)
    # Runs after the response is sent, so the client doesn't wait for SMTP.
    background.add_task(email_service.send_verification_code, user.email, code)
    return ok(user, "Account created. Check your email for the verification code.")


@router.post("/verify-email", response_model=ApiResponse[TokensOut])
def verify_email(data: CodeIn, db: DbSession, background: BackgroundTasks):
    """Confirm the email with the code. Returns tokens, so the user is logged in right away."""
    user, tokens = auth_service.verify_email(db, data.email, data.code)
    background.add_task(email_service.send_welcome, user.email, user.full_name)
    return ok(tokens, "Email verified")


@router.post("/resend-verification", response_model=ApiResponse[None], status_code=status.HTTP_202_ACCEPTED)
def resend_verification(data: EmailIn, db: DbSession, background: BackgroundTasks):
    code = auth_service.resend_verification(db, data.email)
    if code:
        background.add_task(email_service.send_verification_code, data.email, code)
    return ok(None, CODE_SENT)


@router.post("/login", response_model=ApiResponse[TokensOut])
def login(data: LoginIn, db: DbSession):
    """Email + password login. Returns an access token (short) and a refresh token (long)."""
    return ok(auth_service.login_with_password(db, data.email, data.password), "Logged in")


@router.post("/login/code", response_model=ApiResponse[None], status_code=status.HTTP_202_ACCEPTED)
def request_login_code(data: EmailIn, db: DbSession, background: BackgroundTasks):
    """Passwordless login, step 1: email a 6-digit code (works for new emails too)."""
    code = auth_service.request_login_code(db, data.email)
    background.add_task(email_service.send_login_code, data.email, code)
    return ok(None, CODE_SENT)


@router.post("/login/code/verify", response_model=ApiResponse[TokensOut])
def login_with_code(data: CodeIn, db: DbSession):
    """Passwordless login, step 2: exchange the code for tokens. Creates the account on first login."""
    return ok(auth_service.login_with_code(db, data.email, data.code), "Logged in")


@router.post("/refresh", response_model=ApiResponse[TokensOut])
def refresh(data: RefreshIn, db: DbSession):
    """Get a new token pair with a refresh token (call it when the access token expires)."""
    return ok(auth_service.refresh_tokens(db, data.refresh_token))


@router.post("/forgot-password", response_model=ApiResponse[None], status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: EmailIn, db: DbSession, background: BackgroundTasks):
    code = auth_service.forgot_password(db, data.email)
    if code:
        background.add_task(email_service.send_password_reset_code, data.email, code)
    return ok(None, CODE_SENT)


@router.post("/reset-password", response_model=ApiResponse[None])
def reset_password(data: ResetPasswordIn, db: DbSession, background: BackgroundTasks):
    user = auth_service.reset_password(db, data.email, data.code, data.new_password)
    background.add_task(email_service.send_password_changed, user.email)
    return ok(None, "Password updated. You can log in with the new password.")
