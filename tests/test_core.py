"""The response envelope, error handlers, middleware, emails and migrations."""

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.exceptions import ConflictError
from app.main import create_app
from app.services import email_service
from tests.conftest import API

ROOT = Path(__file__).resolve().parent.parent


def test_health(client):
    body = client.get("/health").json()
    assert body == {
        "success": True,
        "message": None,
        "data": {"status": "ok", "database": "ok", "environment": "test"},
    }


def test_unknown_route_and_wrong_method_use_the_envelope(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert r.json()["success"] is False and r.json()["error"]["code"] == "not_found"
    r = client.get(f"{API}/auth/login")
    assert r.status_code == 405 and r.json()["error"]["code"] == "method_not_allowed"


def test_request_id_header_and_in_errors(client):
    r = client.get("/does-not-exist", headers={"X-Request-ID": "trace-123"})
    assert r.headers["X-Request-ID"] == "trace-123"
    assert r.json()["error"]["request_id"] == "trace-123"
    assert "X-Process-Time-Ms" in r.headers


def test_cors_preflight(client):
    r = client.options(
        f"{API}/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_app_error_and_unhandled_error_handlers():
    app = create_app()

    @app.get("/boom-conflict")
    def conflict():
        raise ConflictError("Already there", code="already_there", details={"id": 7})

    @app.get("/boom-crash")
    def crash():
        raise RuntimeError("secret internals")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/boom-conflict")
    assert r.status_code == 409
    assert r.json() == {
        "success": False,
        "message": "Already there",
        "error": {"code": "already_there", "details": {"id": 7}, "request_id": r.headers["X-Request-ID"]},
    }

    r = client.get("/boom-crash")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret" not in r.text  # internals never leak


def test_openapi_documents_envelope_and_errors(client):
    spec = client.get("/openapi.json").json()
    login = spec["paths"][f"{API}/auth/login"]["post"]["responses"]
    assert "401" in login and "422" in login
    assert "ErrorResponse" in spec["components"]["schemas"]


def test_email_templates_escape_html():
    html = email_service.render(
        "notice.html", "Hi", title="<script>x</script>", body="b", link="http://x", link_text="go"
    )
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_console_backend_prints(capsys, monkeypatch):
    monkeypatch.setattr(email_service.settings, "EMAIL_BACKEND", "console")
    email_service.send_login_code("dev@example.com", "123456")
    out = capsys.readouterr().out
    assert "[DEV EMAIL] to=dev@example.com" in out and "123456" in out


def test_smtp_backend_sends_multipart(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["server"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = user

        def send_message(self, message):
            sent["message"] = message

    s = email_service.settings
    monkeypatch.setattr(s, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(s, "SMTP_USER", "mailer")
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    email_service.send_password_reset_code("dev@example.com", "654321")

    message = sent["message"]
    assert sent["tls"] and sent["login"] == "mailer"
    assert message["To"] == "dev@example.com"
    assert message.get_body(("plain",)).get_content().count("654321") == 1
    assert "654321" in message.get_body(("html",)).get_content()


def test_smtp_failure_is_logged_not_raised(monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(email_service.settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(email_service.smtplib, "SMTP", broken)
    email_service.send_welcome("dev@example.com", None)  # must not raise
    assert "Failed to send email" in caplog.text


def test_migrations_match_the_models(tmp_path):
    """`alembic upgrade head` on an empty DB, then `alembic check` finds no drift."""
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path}/migrations.db"}
    for args in (["upgrade", "head"], ["check"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stdout + result.stderr
