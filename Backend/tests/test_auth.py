"""Epic 1 - accounts and access (US-01, US-02, US-03)."""

from tests.conftest import PASSWORD


def test_register_returns_the_new_staff_without_the_password(client):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ali@example.com"
    # US-01: a hash must never leave the API, under any field name.
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_returns_409(client):
    body = {"name": "Ali", "email": "ali@example.com", "password": PASSWORD}
    client.post("/auth/register", json=body)

    response = client.post("/auth/register", json=body)
    assert response.status_code == 409


def test_duplicate_email_is_case_insensitive(client):
    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
    )
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ALI@EXAMPLE.COM", "password": PASSWORD},
    )
    assert response.status_code == 409


def test_short_password_returns_422(client):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": "abc"},
    )
    assert response.status_code == 422
    # US-01 asks for a field-level error, not just a bare 422.
    assert response.json()["detail"][0]["loc"][-1] == "password"


def test_login_returns_a_bearer_token(client, ali):
    assert "token" in ali and ali["token"]


def test_password_is_not_stored_in_plaintext(client, db):
    from src.models import Staff

    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
    )
    staff = db.query(Staff).filter(Staff.email == "ali@example.com").first()
    assert staff.password_hash != PASSWORD
    assert PASSWORD not in staff.password_hash


def test_wrong_password_and_unknown_email_give_the_same_401(client):
    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
    )

    wrong_password = client.post(
        "/auth/login", json={"email": "ali@example.com", "password": "wrongpassword"}
    )
    unknown_email = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # US-02: identical, or the response tells an attacker which accounts exist.
    assert wrong_password.json() == unknown_email.json()


def test_tampered_token_returns_401(client, ali):
    bad = {"token": ali["token"][:-4] + "aaaa"}
    assert client.get("/clients", headers=bad).status_code == 401


def test_garbage_token_returns_401(client):
    assert client.get("/clients", headers={"token": "not-a-token"}).status_code == 401


# US-03: every data route, not just the ones that were convenient to check.
def test_all_data_routes_reject_a_missing_token(client):
    routes = [
        ("get", "/clients"),
        ("get", "/clients/1"),
        ("post", "/clients/registration"),
        ("patch", "/clients/1"),
        ("delete", "/clients/1"),
        ("get", "/cases"),
        ("get", "/cases/1"),
        ("post", "/cases/registration"),
        ("patch", "/cases/1"),
        ("patch", "/cases/1/status"),
        ("post", "/cases/1/notes"),
        ("delete", "/notes/1"),
    ]
    for method, path in routes:
        response = client.request(method.upper(), path, json={})
        assert response.status_code == 401, f"{method.upper()} {path} gave {response.status_code}"
