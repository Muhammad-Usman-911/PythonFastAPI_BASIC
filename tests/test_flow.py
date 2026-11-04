import os
import tempfile

# Must be set before the app is imported
_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["SMTP_HOST"] = ""

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app
from app.services import email_service

client = TestClient(app)
sent: dict[str, str] = {}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sent.clear()
    monkeypatch.setattr(email_service, "send_otp_email", lambda e, c: sent.__setitem__(e, c))


def login(email="a@test.com"):
    assert client.post("/auth/request-otp", json={"email": email}).status_code == 202
    r = client.post("/auth/verify-otp", json={"email": email, "code": sent[email]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_tasks_require_auth():
    assert client.get("/tasks").status_code == 401
    r = client.get("/tasks", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_otp_login_and_me():
    h = login()
    r = client.get("/auth/me", headers=h)
    assert r.status_code == 200 and r.json()["email"] == "a@test.com"


def test_wrong_otp_and_attempt_limit():
    client.post("/auth/request-otp", json={"email": "b@test.com"})
    real = sent["b@test.com"]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(5):
        assert client.post("/auth/verify-otp", json={"email": "b@test.com", "code": wrong}).status_code == 401
    # after 5 failures even the right code is rejected
    assert client.post("/auth/verify-otp", json={"email": "b@test.com", "code": real}).status_code == 401


def test_otp_cannot_be_reused():
    client.post("/auth/request-otp", json={"email": "c@test.com"})
    code = sent["c@test.com"]
    assert client.post("/auth/verify-otp", json={"email": "c@test.com", "code": code}).status_code == 200
    assert client.post("/auth/verify-otp", json={"email": "c@test.com", "code": code}).status_code == 401


def test_resend_cooldown():
    assert client.post("/auth/request-otp", json={"email": "d@test.com"}).status_code == 202
    r = client.post("/auth/request-otp", json={"email": "d@test.com"})
    assert r.status_code == 429


def test_bad_code_format_and_email():
    assert client.post("/auth/verify-otp", json={"email": "a@test.com", "code": "12"}).status_code == 422
    assert client.post("/auth/request-otp", json={"email": "nope"}).status_code == 422


def test_task_crud_and_isolation():
    h1 = login("u1@test.com")
    h2 = login("u2@test.com")

    r = client.post("/tasks", json={"title": "one", "description": "d"}, headers=h1)
    assert r.status_code == 201
    tid = r.json()["id"]
    client.post("/tasks", json={"title": "two"}, headers=h1)

    page = client.get("/tasks?limit=1", headers=h1).json()
    assert page["total"] == 2 and len(page["items"]) == 1

    assert client.patch(f"/tasks/{tid}", json={"done": True}, headers=h1).json()["done"] is True
    assert client.get("/tasks?done=true", headers=h1).json()["total"] == 1

    # user 2 sees nothing and cannot touch user 1's task
    assert client.get("/tasks", headers=h2).json()["total"] == 0
    r = client.get(f"/tasks/{tid}", headers=h2)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert client.delete(f"/tasks/{tid}", headers=h2).status_code == 404

    assert client.delete(f"/tasks/{tid}", headers=h1).status_code == 204
    assert client.get(f"/tasks/{tid}", headers=h1).status_code == 404


def test_task_validation():
    h = login()
    assert client.post("/tasks", json={"title": ""}, headers=h).status_code == 422
    assert client.post("/tasks", json={}, headers=h).status_code == 422
