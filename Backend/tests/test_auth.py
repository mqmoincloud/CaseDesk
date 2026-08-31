"""Epic 1 - accounts and access (US-01, US-02, US-03)."""

from tests.conftest import PASSWORD


def test_register_returns_the_new_staff_without_the_password(client, admin):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
        headers=admin,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ali@example.com"
    # US-01: a hash must never leave the API, under any field name.
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_returns_409(client, admin):
    body = {"name": "Ali", "email": "ali@example.com", "password": PASSWORD}
    client.post("/auth/register", json=body, headers=admin)

    response = client.post("/auth/register", json=body, headers=admin)
    assert response.status_code == 409


def test_duplicate_email_is_case_insensitive(client, admin):
    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
        headers=admin,
    )
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ALI@EXAMPLE.COM", "password": PASSWORD},
        headers=admin,
    )
    assert response.status_code == 409


def test_short_password_returns_422(client, admin):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": "abc"},
        headers=admin,
    )
    assert response.status_code == 422
    # US-01 asks for a field-level error, not just a bare 422.
    assert "password" in response.json()["error"]["fields"]


def test_login_returns_a_bearer_token(client, ali):
    assert ali["Authorization"].startswith("Bearer ")


def test_password_is_not_stored_in_plaintext(client, db, admin):
    from src.models import Staff

    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
        headers=admin,
    )
    staff = db.query(Staff).filter(Staff.email == "ali@example.com").first()
    assert staff.password_hash != PASSWORD
    assert PASSWORD not in staff.password_hash


def test_wrong_password_and_unknown_email_give_the_same_401(client, admin):
    client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": PASSWORD},
        headers=admin,
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
    bad = {"Authorization": ali["Authorization"][:-4] + "aaaa"}
    assert client.get("/clients", headers=bad).status_code == 401


def test_garbage_token_returns_401(client):
    assert client.get("/clients", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


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


def test_staff_list_is_available_for_the_assignee_picker(client, ali, sara):
    response = client.get("/staff", headers=ali)
    assert response.status_code == 200

    names = [row["name"] for row in response.json()]
    # Everyone, not just the caller - a case can be assigned to any colleague.
    assert "Ali Khan" in names
    assert "Sara Sheikh" in names


def test_staff_list_sends_only_what_the_picker_needs(client, ali):
    # /staff fills the assignee dropdown, so it carries a name and an id and
    # nothing else - no password hash, and no colleague's email address.
    body = client.get("/staff", headers=ali).json()
    for row in body:
        assert set(row.keys()) == {"id", "name"}


def test_me_says_who_you_are(client, ali):
    body = client.get("/me", headers=ali).json()
    assert body["email"] == "ali@example.com"
    assert body["role"] == "staff"
    assert "password_hash" not in body


def test_me_marks_an_admin_as_one(client, admin):
    assert client.get("/me", headers=admin).json()["role"] == "admin"


def test_me_needs_a_token(client):
    assert client.get("/me").status_code == 401


def test_staff_list_requires_a_token(client):
    assert client.get("/staff").status_code == 401


def test_no_token_header_says_so(client):
    # Nothing was sent, so "invalid or expired" would point at the wrong thing.
    response = client.get("/clients")
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Not authenticated"


# --- bcrypt silently drops anything past 72 bytes ---


def test_a_password_longer_than_bcrypt_can_hold_is_rejected(client, admin):
    """Without this a 100-character password would be accepted, bcrypt would
    keep the first 72 bytes and drop the rest, and anyone who knew those 72
    could type anything for the last 28 and still log in. StaffUpdate and
    PasswordChange already had the cap; only register was missing it."""
    response = client.post(
        "/auth/register",
        json={"name": "Long", "email": "long@example.com", "password": "A" * 100},
        headers=admin,
    )

    assert response.status_code == 422
    assert "password" in response.json()["error"]["fields"]
