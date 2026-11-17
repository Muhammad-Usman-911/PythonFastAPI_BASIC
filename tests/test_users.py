from sqlalchemy import update

from app.models.user import User
from tests.conftest import API, PASSWORD, auth_header, last_code, verified_user


def test_me_requires_auth(client):
    r = client.get(f"{API}/users/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


def test_read_and_update_me(client):
    h = auth_header(verified_user(client))
    me = client.get(f"{API}/users/me", headers=h).json()["data"]
    assert me["email"] == "ada@example.com" and me["has_password"] is True

    r = client.patch(f"{API}/users/me", json={"full_name": "Ada Lovelace"}, headers=h)
    assert r.status_code == 200 and r.json()["data"]["full_name"] == "Ada Lovelace"
    assert r.json()["message"] == "Profile updated"


def test_change_password(client):
    h = auth_header(verified_user(client))
    r = client.post(
        f"{API}/users/me/change-password",
        json={"current_password": "Wrong1234", "new_password": "N3wPassw0rd"},
        headers=h,
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "wrong_password"

    r = client.post(
        f"{API}/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": "N3wPassw0rd"},
        headers=h,
    )
    assert r.status_code == 200
    assert (
        client.post(
            f"{API}/auth/login", json={"email": "ada@example.com", "password": "N3wPassw0rd"}
        ).status_code
        == 200
    )


def test_code_user_can_set_a_first_password(client):
    client.post(f"{API}/auth/login/code", json={"email": "otp@example.com"})
    r = client.post(
        f"{API}/auth/login/code/verify",
        json={"email": "otp@example.com", "code": last_code("otp@example.com")},
    )
    h = auth_header(r.json()["data"])
    r = client.post(f"{API}/users/me/change-password", json={"new_password": "Fresh1234"}, headers=h)
    assert r.status_code == 200
    assert (
        client.post(
            f"{API}/auth/login", json={"email": "otp@example.com", "password": "Fresh1234"}
        ).status_code
        == 200
    )


def test_admin_list_is_role_protected_and_paginated(client, db):
    h = auth_header(verified_user(client))
    verified_user(client, "bob@example.com")
    r = client.get(f"{API}/users", headers=h)
    assert r.status_code == 403 and r.json()["error"]["code"] == "insufficient_role"

    db.execute(update(User).where(User.email == "ada@example.com").values(role="admin"))
    db.commit()
    page = client.get(f"{API}/users?limit=1&offset=1", headers=h).json()["data"]
    assert page["total"] == 2 and page["limit"] == 1 and len(page["items"]) == 1
    assert page["items"][0]["email"] == "bob@example.com"

    r = client.get(f"{API}/users?limit=500", headers=h)
    assert r.status_code == 422
