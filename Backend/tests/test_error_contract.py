"""NF-05 - one error shape across the whole API.

Every failure, whoever raised it, must come back as:

    {"error": {"status": <int>, "message": <str>, "fields": {<field>: <msg>}}}

Without a test like this the contract quietly drifts: someone adds an endpoint,
FastAPI's default shape leaks out of it, and nothing complains.
"""

import pytest


def assert_error_shape(response, status):
    body = response.json()

    assert response.status_code == status
    assert set(body.keys()) == {"error"}, f"unexpected top-level keys: {list(body)}"

    error = body["error"]
    assert set(error.keys()) == {"status", "message", "fields"}
    assert error["status"] == status
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["fields"], dict)


def test_401_uses_the_shape(client):
    assert_error_shape(client.get("/clients"), 401)


def test_404_uses_the_shape(client, ali):
    assert_error_shape(client.get("/clients/99999", headers=ali), 404)


def test_409_duplicate_uses_the_shape(client, ali):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": "password123"},
    )
    assert_error_shape(response, 409)


def test_409_bad_transition_uses_the_shape(client, ali, ali_case_id):
    response = client.patch(
        f"/cases/{ali_case_id}/status", json={"status": "Closed"}, headers=ali
    )
    assert_error_shape(response, 409)


def test_422_uses_the_shape_and_names_the_field(client, ali):
    response = client.post(
        "/clients/registration", json={"name": "X", "email": "not-an-email"}, headers=ali
    )
    assert_error_shape(response, 422)
    # A validation error is the one case that fills in fields.
    assert "email" in response.json()["error"]["fields"]


def test_422_on_a_bad_path_parameter_uses_the_shape(client, ali):
    # /clients/{id} expects an int, so "abc" fails before our code runs.
    response = client.get("/clients/abc", headers=ali)
    assert_error_shape(response, 422)


# These two come from Starlette itself, not from anything we raise. They are the
# reason the handler is registered on Starlette's HTTPException rather than
# FastAPI's subclass - registering on the subclass leaves them in the old shape.
def test_unknown_route_uses_the_shape(client):
    assert_error_shape(client.get("/no-such-route"), 404)


def test_wrong_method_uses_the_shape(client, ali):
    assert_error_shape(client.delete("/clients", headers=ali), 405)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/clients"),
        ("get", "/cases"),
        ("get", "/staff"),
        ("post", "/clients/registration"),
        ("delete", "/notes/1"),
    ],
)
def test_every_route_family_reports_missing_auth_the_same_way(client, method, path):
    assert_error_shape(client.request(method.upper(), path, json={}), 401)
