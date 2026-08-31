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


def test_409_duplicate_uses_the_shape(client, ali, admin):
    response = client.post(
        "/auth/register",
        json={"name": "Ali", "email": "ali@example.com", "password": "password123"},
        headers=admin,
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


def test_a_limit_outside_the_allowed_range_uses_the_shape(client, ali):
    # limit is bounded by Query(ge=1, le=100), so FastAPI raises the same
    # validation error as any bad body field - and it names the field.
    response = client.get("/clients?limit=101", headers=ali)
    assert_error_shape(response, 422)
    assert "limit" in response.json()["error"]["fields"]


# --- an unexpected crash uses the same shape ---


def test_an_unexpected_error_uses_the_shape(client):
    """NF-05 asks for one error shape across the whole API.

    Only HTTPException and validation were handled before, so any bug answered in
    FastAPI's own shape - meaning a front end taught to read data.error.message
    everywhere found nothing there exactly when something had really broken.

    Yahan ek route jaan-boojh kar phaad kar dekhte hain. raise_server_exceptions
    ko band karna zaroori hai, warna TestClient exception ko aage phenk deta hai
    handler chalne ke bajaye - bilkul waise hi jaise asli server pe hota hai.
    """
    from fastapi.testclient import TestClient

    from src.main import app

    @app.get("/boom-for-tests")
    def boom():
        raise RuntimeError("something broke")

    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get("/boom-for-tests")

    assert response.status_code == 500

    error = response.json()["error"]
    assert error["status"] == 500
    assert error["fields"] == {}
    # The real cause belongs in the log, not in the response.
    assert "something broke" not in error["message"]
