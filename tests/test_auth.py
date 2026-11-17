from datetime import timedelta

import jwt
from sqlalchemy import update

from app.core.config import settings
from app.core.utils import utcnow
from app.models.otp import OtpCode
from app.models.user import User
from app.services import email_service
from tests.conftest import API, PASSWORD, auth_header, last_code, register, verified_user


# ---------- register + verify email ----------
def test_register_returns_user_and_emails_a_code(client):
    body = register(client, "New@Example.com")
    assert body["success"] is True
    assert body["data"]["email"] == "new@example.com"  # normalised
    assert body["data"]["is_verified"] is False
    assert "hashed_password" not in body["data"]
    assert email_service.outbox[-1].subject.startswith("Verify your email")
    assert len(last_code("new@example.com")) == 6


def test_register_duplicate_email(client):
    register(client)
    r = client.post(f"{API}/auth/register", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_register_weak_password_lists_field_errors(client):
    r = client.post(f"{API}/auth/register", json={"email": "ada@example.com", "password": "short"})
    assert r.status_code == 422
    details = r.json()["error"]["details"]
    assert details[0]["field"] == "body.password"
    assert "at least 8" in details[0]["message"]
    r = client.post(f"{API}/auth/register", json={"email": "ada@example.com", "password": "lettersonly"})
    assert "letter and one number" in r.json()["error"]["details"][0]["message"]


def test_login_blocked_until_verified_then_works(client):
    register(client)
    r = client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_not_verified"

    r = client.post(
        f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": last_code("ada@example.com")}
    )
    assert r.status_code == 200
    assert email_service.outbox[-1].subject.startswith("Welcome")

    r = client.post(f"{API}/auth/login", json={"email": "ADA@example.com", "password": PASSWORD})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["token_type"] == "bearer" and data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_verify_email_wrong_code(client):
    register(client)
    code = last_code("ada@example.com")
    wrong = "000000" if code != "000000" else "111111"
    r = client.post(f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": wrong})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_code"


def test_resend_verification_same_answer_for_unknown_email(client):
    register(client)
    client.post(
        f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": last_code("ada@example.com")}
    )
    sent_before = len(email_service.outbox)
    for email in ("ada@example.com", "nobody@example.com"):  # verified / unknown
        r = client.post(f"{API}/auth/resend-verification", json={"email": email})
        assert r.status_code == 202
    assert len(email_service.outbox) == sent_before  # nothing sent


def test_resend_verification_cooldown_then_new_code(client, db):
    register(client)
    r = client.post(f"{API}/auth/resend-verification", json={"email": "ada@example.com"})
    assert r.status_code == 429
    assert r.json()["error"]["details"]["retry_after_seconds"] == 60

    # pretend the first code was sent long ago
    db.execute(update(OtpCode).values(created_at=utcnow() - timedelta(minutes=5)))
    db.commit()
    old = last_code("ada@example.com")
    assert (
        client.post(f"{API}/auth/resend-verification", json={"email": "ada@example.com"}).status_code == 202
    )
    new = last_code("ada@example.com")
    if old != new:  # the old code is cancelled
        r = client.post(f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": old})
        assert r.status_code == 400
    assert (
        client.post(f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": new}).status_code
        == 200
    )


def test_wrong_password_and_unknown_email_look_the_same(client):
    verified_user(client)
    a = client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": "Wrong123"})
    b = client.post(f"{API}/auth/login", json={"email": "ghost@example.com", "password": "Wrong123"})
    assert a.status_code == b.status_code == 401
    assert a.json()["message"] == b.json()["message"]
    assert a.json()["error"]["code"] == "invalid_credentials"


def test_disabled_user_cannot_login(client, db):
    verified_user(client)
    db.execute(update(User).values(is_active=False))
    db.commit()
    r = client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_disabled"


# ---------- passwordless login ----------
def test_code_login_creates_verified_user(client):
    r = client.post(f"{API}/auth/login/code", json={"email": "otp@example.com"})
    assert r.status_code == 202
    assert email_service.outbox[-1].subject.endswith("login code")
    r = client.post(
        f"{API}/auth/login/code/verify",
        json={"email": "otp@example.com", "code": last_code("otp@example.com")},
    )
    assert r.status_code == 200
    me = client.get(f"{API}/users/me", headers=auth_header(r.json()["data"])).json()["data"]
    assert me["is_verified"] is True and me["has_password"] is False


def test_code_cannot_be_reused_and_attempts_are_limited(client):
    client.post(f"{API}/auth/login/code", json={"email": "otp@example.com"})
    code = last_code("otp@example.com")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        r = client.post(f"{API}/auth/login/code/verify", json={"email": "otp@example.com", "code": wrong})
        assert r.status_code == 400
    # after too many failures even the right code is refused
    r = client.post(f"{API}/auth/login/code/verify", json={"email": "otp@example.com", "code": code})
    assert r.status_code == 400


def test_code_used_once(client):
    client.post(f"{API}/auth/login/code", json={"email": "otp@example.com"})
    code = last_code("otp@example.com")
    payload = {"email": "otp@example.com", "code": code}
    assert client.post(f"{API}/auth/login/code/verify", json=payload).status_code == 200
    assert client.post(f"{API}/auth/login/code/verify", json=payload).status_code == 400


def test_expired_code(client, db):
    client.post(f"{API}/auth/login/code", json={"email": "otp@example.com"})
    db.execute(update(OtpCode).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    r = client.post(
        f"{API}/auth/login/code/verify",
        json={"email": "otp@example.com", "code": last_code("otp@example.com")},
    )
    assert r.status_code == 400


def test_code_format_is_validated(client):
    r = client.post(f"{API}/auth/login/code/verify", json={"email": "otp@example.com", "code": "12"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "body.code"


# ---------- tokens ----------
def test_refresh_gives_new_tokens_and_types_are_enforced(client):
    tokens = verified_user(client)
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200 and "access_token" in r.json()["data"]

    # an access token is not a refresh token, and vice versa
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"
    r = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401


def test_expired_and_garbage_tokens(client):
    verified_user(client)
    expired = jwt.encode(
        {"sub": "1", "type": "access", "exp": utcnow() - timedelta(minutes=1)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    r = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.json()["error"]["code"] == "token_expired"
    r = client.get(f"{API}/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


# ---------- forgot / reset password ----------
def test_forgot_and_reset_password(client):
    verified_user(client)
    r = client.post(f"{API}/auth/forgot-password", json={"email": "ada@example.com"})
    assert r.status_code == 202
    code = last_code("ada@example.com")

    r = client.post(
        f"{API}/auth/reset-password",
        json={"email": "ada@example.com", "code": code, "new_password": "N3wPassw0rd"},
    )
    assert r.status_code == 200
    assert email_service.outbox[-1].subject.endswith("password was changed")

    assert (
        client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": PASSWORD}).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/auth/login", json={"email": "ada@example.com", "password": "N3wPassw0rd"}
        ).status_code
        == 200
    )


def test_forgot_password_unknown_email_sends_nothing(client):
    r = client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 202 and email_service.outbox == []


def test_reset_password_code_is_purpose_bound(client):
    """A login code can't be used to reset a password."""
    verified_user(client)
    client.post(f"{API}/auth/login/code", json={"email": "ada@example.com"})
    r = client.post(
        f"{API}/auth/reset-password",
        json={
            "email": "ada@example.com",
            "code": last_code("ada@example.com"),
            "new_password": "N3wPassw0rd",
        },
    )
    assert r.status_code == 400
