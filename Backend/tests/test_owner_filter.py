"""The cases list can be narrowed to one person's own cases.

An assignee sees other people's cases in this list, so "created by me" and
"assigned to me" are two different questions and need two different filters.
"""

import pytest


@pytest.fixture
def ali_id(client, ali, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "ali@example.com").first().id


@pytest.fixture
def sara_id(client, sara, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "sara@example.com").first().id


@pytest.fixture
def mixed_cases(client, ali, sara, ali_id, sara_id):
    """One case Ali owns and assigned to Sara, one Sara owns and assigned to Ali.

    Sara can see both: one because she owns it, one because it is assigned to
    her. That is what makes the filter worth having.
    """
    ali_client = client.post(
        "/clients/registration", json={"name": "Ali Client"}, headers=ali
    ).json()["id"]

    sara_client = client.post(
        "/clients/registration", json={"name": "Sara Client"}, headers=sara
    ).json()["id"]

    client.post(
        "/cases/registration",
        json={"client_id": ali_client, "title": "Ali's case",
              "case_type": "Civil", "assignee_id": sara_id},
        headers=ali,
    )
    client.post(
        "/cases/registration",
        json={"client_id": sara_client, "title": "Sara's case",
              "case_type": "Civil", "assignee_id": ali_id},
        headers=sara,
    )


def titles(body):
    return sorted(c["title"] for c in body["items"])


def test_sara_sees_both_without_a_filter(client, sara, mixed_cases):
    body = client.get("/cases", headers=sara).json()

    assert titles(body) == ["Ali's case", "Sara's case"]
    assert body["total"] == 2


def test_owner_narrows_to_the_ones_she_created(client, sara, sara_id, mixed_cases):
    body = client.get(f"/cases?owner={sara_id}", headers=sara).json()

    assert titles(body) == ["Sara's case"]
    assert body["total"] == 1


def test_assignee_narrows_to_the_ones_given_to_her(client, sara, sara_id, mixed_cases):
    body = client.get(f"/cases?assignee={sara_id}", headers=sara).json()

    assert titles(body) == ["Ali's case"]
    assert body["total"] == 1


def test_owner_and_status_combine(client, sara, sara_id, mixed_cases):
    """The new filter has to narrow alongside the others, not replace them."""
    body = client.get(f"/cases?owner={sara_id}&status=Intake", headers=sara).json()
    assert titles(body) == ["Sara's case"]

    body = client.get(f"/cases?owner={sara_id}&status=Closed", headers=sara).json()
    assert body["items"] == []
    assert body["total"] == 0


def test_owner_cannot_reach_someone_elses_cases(client, sara, ali_id, mixed_cases):
    """Filtering by Ali returns only what Sara was already allowed to see."""
    body = client.get(f"/cases?owner={ali_id}", headers=sara).json()

    assert titles(body) == ["Ali's case"]


def test_an_admin_can_filter_by_any_owner(client, admin, ali_id, sara_id, mixed_cases):
    ali_only = client.get(f"/cases?owner={ali_id}", headers=admin).json()
    sara_only = client.get(f"/cases?owner={sara_id}", headers=admin).json()

    assert titles(ali_only) == ["Ali's case"]
    assert titles(sara_only) == ["Sara's case"]


def test_a_bad_owner_value_is_a_422(client, ali):
    assert client.get("/cases?owner=0", headers=ali).status_code == 422
    assert client.get("/cases?owner=abc", headers=ali).status_code == 422
