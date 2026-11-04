import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, code: str) -> None:
    # Dev mode: no SMTP configured, print the code to the console.
    if not settings.SMTP_HOST:
        print(f"\n[DEV] OTP for {to_email}: {code}\n", flush=True)
        return

    msg = EmailMessage()
    msg["Subject"] = "Your login code"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg.set_content(
        f"Your verification code is {code}.\n"
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this, ignore this email."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        # Runs in a background task: log it, the client already got a response.
        logger.exception("Failed to send OTP email to %s", to_email)
