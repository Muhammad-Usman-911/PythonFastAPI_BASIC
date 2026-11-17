"""Shared test setup. Node equivalent: a Jest `setupFiles` + supertest helpers.

- Settings are set through env vars BEFORE the app is imported.
- Each test gets empty tables (fast SQLite file in a temp folder).
- EMAIL_BACKEND=memory: emails land in `email_service.outbox`, so tests can read codes.
"""

import os
import re
import tempfile

_tmp = tempfile.mkdtemp(prefix="fastapi-starter-tests-")
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
        "JWT_SECRET": "test-secret-that-is-at-least-32-characters-long",
        "EMAIL_BACKEND": "memory",
        "OTP_RESEND_SECONDS": "60",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402, F401  (register tables)
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import email_service  # noqa: E402

API = "/api/v1"
PASSWORD = "Passw0rd!"


@pytest.fixture(autouse=True)
def clean_state():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    email_service.outbox.clear()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def last_code(email: str) -> str:
    """Read the 6-digit code from the newest email sent to `email`."""
    for sent in reversed(email_service.outbox):
        if sent.to == email:
            match = re.search(r"\b(\d{6})\b", sent.text)
            assert match, f"no code in email: {sent.subject}"
            return match.group(1)
    raise AssertionError(f"no email sent to {email}")


def register(client: TestClient, email: str = "ada@example.com", password: str = PASSWORD) -> dict:
    r = client.post(f"{API}/auth/register", json={"email": email, "password": password, "full_name": "Ada"})
    assert r.status_code == 201, r.text
    return r.json()


def verified_user(client: TestClient, email: str = "ada@example.com") -> dict:
    """Register + verify. Returns the token data."""
    register(client, email)
    r = client.post(f"{API}/auth/verify-email", json={"email": email, "code": last_code(email)})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def auth_header(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
