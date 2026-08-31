"""The profile screen - reading and changing your own account.

Nothing here takes an id. Whoever the token belongs to is the row that gets
read or written, so there is no way to aim any of it at somebody else.
"""

from tests.conftest import PASSWORD, login


def test_me_returns_your_own_details(client, ali):
    body = client.get("/me", headers=ali).json()

    assert body["name"] == "Ali Khan"
    assert body["email"] == "ali@example.com"
    assert body["role"] == "staff"
    assert body["created_at"] is not None
    assert "password_hash" not in body


def test_you_can_change_your_name(client, ali):
    response = client.patch("/me", json={"name": "Ali R. Khan"}, headers=ali)

    assert response.status_code == 200
    assert response.json()["name"] == "Ali R. Khan"
    # And it stuck, rather than only looking right in the response.
    assert client.get("/me", headers=ali).json()["name"] == "Ali R. Khan"


def test_an_empty_name_is_rejected(client, ali):
    assert client.patch("/me", json={"name": ""}, headers=ali).status_code == 422


def test_changing_your_name_does_not_touch_your_role(client, ali):
    client.patch("/me", json={"name": "Renamed"}, headers=ali)
    assert client.get("/me", headers=ali).json()["role"] == "staff"


def test_a_staff_member_cannot_make_themselves_admin(client, ali):
    # role is not in ProfileUpdate at all, so it is dropped rather than applied.
    client.patch("/me", json={"name": "Sneaky", "role": "admin"}, headers=ali)
    assert client.get("/me", headers=ali).json()["role"] == "staff"


def test_profile_needs_a_token(client):
    assert client.get("/me").status_code == 401
    assert client.patch("/me", json={"name": "X"}).status_code == 401


# --- password ---

def test_you_can_change_your_password(client, ali):
    response = client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnewpass"},
        headers=ali,
    )
    assert response.status_code == 200

    # The new one works and the old one does not.
    assert client.post(
        "/auth/login", json={"email": "ali@example.com", "password": "brandnewpass"}
    ).status_code == 200
    assert client.post(
        "/auth/login", json={"email": "ali@example.com", "password": PASSWORD}
    ).status_code == 401


def test_the_wrong_current_password_is_refused(client, ali):
    response = client.post(
        "/me/password",
        json={"current_password": "notmypassword", "new_password": "brandnewpass"},
        headers=ali,
    )
    # 422, not 403. The caller is authenticated and changing their own
    # password, so nothing is forbidden - one field in the body is wrong,
    # which is what 422 means in NF-05. 403 is not in that table at all.
    assert response.status_code == 422

    # And nothing changed.
    assert login(client, "ali@example.com") is not None


def test_a_short_new_password_is_rejected(client, ali):
    response = client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "abc"},
        headers=ali,
    )
    assert response.status_code == 422


def test_the_new_password_is_stored_hashed(client, ali, db):
    from src.models import Staff

    client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnewpass"},
        headers=ali,
    )

    row = db.query(Staff).filter(Staff.email == "ali@example.com").first()
    assert row.password_hash != "brandnewpass"
    assert "brandnewpass" not in row.password_hash


def test_changing_your_password_does_not_touch_anyone_else(client, ali, sara):
    client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnewpass"},
        headers=ali,
    )

    assert client.post(
        "/auth/login", json={"email": "sara@example.com", "password": PASSWORD}
    ).status_code == 200


def test_an_admin_uses_the_same_profile_routes(client, admin):
    assert client.get("/me", headers=admin).json()["role"] == "admin"
    assert client.patch("/me", json={"name": "The Admin"}, headers=admin).status_code == 200


# --- a password change has to kill the older tokens ---


def test_the_old_token_stops_working_after_a_password_change(client, ali):
    """A password is changed to end the old access. If the old token kept
    working the job would be half done - a stolen one would live out its full
    thirty minutes."""
    client.post(
        "/me/password",
        json={"current_password": "password123", "new_password": "brandnew999"},
        headers=ali,
    )

    assert client.get("/me", headers=ali).status_code == 401


def test_the_new_password_gives_a_token_that_works(client, ali):
    client.post(
        "/me/password",
        json={"current_password": "password123", "new_password": "brandnew999"},
        headers=ali,
    )

    token = client.post(
        "/auth/login", json={"email": "ali@example.com", "password": "brandnew999"}
    ).json()["access_token"]

    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_an_admin_reset_also_kills_the_old_token(client, admin, ali, db):
    """Same reason: an admin resets a password when the access has to end."""
    from src.models import Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    client.patch(f"/staff/{ali_id}", json={"password": "resetbyadmin1"}, headers=admin)

    assert client.get("/me", headers=ali).status_code == 401
