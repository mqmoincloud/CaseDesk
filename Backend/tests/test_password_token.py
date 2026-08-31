"""Changing your password must sign out the other sessions, not this one.

`token_version` goes up on every password change, which is the point: any token
issued before it stops working. The catch is that the caller is holding one of
those tokens. Before this, the screen said "Password changed" and the next
request anywhere came back 401.
"""

from tests.conftest import PASSWORD


def test_the_change_hands_back_a_working_token(client, ali):
    response = client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnew999"},
        headers=ali,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    fresh = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/me", headers=fresh).status_code == 200


def test_the_token_that_made_the_change_still_stops_working(client, ali):
    """The new token is a replacement, not an exemption - the old one is dead."""
    client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnew999"},
        headers=ali,
    )

    assert client.get("/me", headers=ali).status_code == 401


def test_the_new_token_survives_a_second_change(client, ali):
    """Two changes in a row: each one hands back a token the next one accepts."""
    first = client.post(
        "/me/password",
        json={"current_password": PASSWORD, "new_password": "brandnew999"},
        headers=ali,
    ).json()

    headers = {"Authorization": f"Bearer {first['access_token']}"}

    second = client.post(
        "/me/password",
        json={"current_password": "brandnew999", "new_password": "thirdpass123"},
        headers=headers,
    )

    assert second.status_code == 200
    assert client.get(
        "/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    ).status_code == 200


def test_a_failed_change_does_not_hand_back_anything(client, ali):
    """The wrong current password is a 422, and the old token keeps working."""
    response = client.post(
        "/me/password",
        json={"current_password": "notmypassword", "new_password": "brandnew999"},
        headers=ali,
    )

    assert response.status_code == 422
    assert "access_token" not in response.json()
    assert client.get("/me", headers=ali).status_code == 200
