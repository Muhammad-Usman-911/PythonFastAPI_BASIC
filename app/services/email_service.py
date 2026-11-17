"""Sending email: templates + one `send_email()` that works with three backends.

Node equivalent: `nodemailer` + handlebars templates.

EMAIL_BACKEND (in .env) decides what `send_email()` does:
- console : print the email in the uvicorn terminal (default; zero setup)
- smtp    : really send it (Gmail, Mailpit, SendGrid/SES/Brevo SMTP, ...)
- memory  : append it to `outbox` (the tests read codes from there)

Emails are sent from a FastAPI BackgroundTask (see app/routers/auth.py): the client
gets its response immediately and SMTP runs after it. Failures are logged, not raised.

Add a new email in 3 steps:
1. (optional) add a template in app/templates/email/ using ${placeholders}
2. write a `send_xxx()` function below that calls `render()` + `send_email()`
3. call it from a service/router with `background.add_task(email_service.send_xxx, ...)`
"""

import html
import logging
import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from functools import cache
from pathlib import Path
from string import Template

from app.core.config import settings

logger = logging.getLogger("app.email")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


@dataclass
class SentEmail:
    to: str
    subject: str
    text: str
    html: str


# Filled only when EMAIL_BACKEND=memory (tests).
outbox: list[SentEmail] = []


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
@cache
def _load(name: str) -> Template:
    return Template((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def render(template: str, subject: str, **values: object) -> str:
    """Fill `template` (values are HTML-escaped) and wrap it in base.html."""
    safe = {key: html.escape(str(value)) for key, value in values.items()}
    content = _load(template).substitute(safe)
    return _load("base.html").substitute(
        subject=html.escape(subject), app_name=html.escape(settings.APP_NAME), content=content
    )


def _html_to_text(markup: str) -> str:
    """Rough plain-text version for email clients that don't show HTML."""
    body = re.sub(r"(?is)<(head|style).*?</\1>", "", markup)
    text = re.sub(r"<[^>]+>", " ", body)
    lines = [" ".join(line.split()) for line in html.unescape(text).splitlines()]
    return "\n".join(line for line in lines if line)


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------
def send_email(to: str, subject: str, html_body: str, text_body: str | None = None) -> None:
    text_body = text_body or _html_to_text(html_body)

    if settings.EMAIL_BACKEND == "memory":
        outbox.append(SentEmail(to=to, subject=subject, text=text_body, html=html_body))
        return

    if settings.EMAIL_BACKEND == "console":
        print(f"\n===== [DEV EMAIL] to={to} | {subject} =====\n{text_body}\n" + "=" * 40, flush=True)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
    message["To"] = to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        smtp_class = smtplib.SMTP_SSL if settings.SMTP_SSL else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_STARTTLS and not settings.SMTP_SSL:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info("Email sent to %s: %s", to, subject)
    except Exception:
        # Runs in a background task: the client already has its response, so log it.
        logger.exception("Failed to send email to %s: %s", to, subject)


# ---------------------------------------------------------------------------
# The emails this app sends
# ---------------------------------------------------------------------------
def _send_code(to: str, code: str, subject: str, title: str, intro: str) -> None:
    body = render(
        "code.html", subject, title=title, intro=intro, code=code, minutes=settings.OTP_EXPIRE_MINUTES
    )
    send_email(to, subject, body)


def send_verification_code(to: str, code: str) -> None:
    _send_code(
        to,
        code,
        f"Verify your email for {settings.APP_NAME}",
        "Confirm your email",
        "Thanks for signing up! Enter this code to verify your email address.",
    )


def send_login_code(to: str, code: str) -> None:
    _send_code(
        to,
        code,
        f"Your {settings.APP_NAME} login code",
        "Your login code",
        "Use this code to sign in. No password needed.",
    )


def send_password_reset_code(to: str, code: str) -> None:
    _send_code(
        to,
        code,
        f"Reset your {settings.APP_NAME} password",
        "Reset your password",
        "We received a request to reset your password. Enter this code to choose a new one.",
    )


def send_welcome(to: str, name: str | None) -> None:
    subject = f"Welcome to {settings.APP_NAME}"
    body = render(
        "notice.html",
        subject,
        title=f"Welcome{', ' + name if name else ''}!",
        body="Your email is verified and your account is ready.",
        link=settings.FRONTEND_URL,
        link_text="Open the app",
    )
    send_email(to, subject, body)


def send_password_changed(to: str) -> None:
    subject = f"Your {settings.APP_NAME} password was changed"
    body = render(
        "notice.html",
        subject,
        title="Password changed",
        body="Your password was just changed. If this wasn't you, reset it now and contact support.",
        link=settings.FRONTEND_URL,
        link_text="Open the app",
    )
    send_email(to, subject, body)
