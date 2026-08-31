"""The assignment record - who assigned whom, and when.

The cases list needs only the latest assignment, but the table keeps the whole
history so the case page can show a timeline. These tests pin both ends: every
real change writes a row, and a non-change writes none.
"""

import pytest


@pytest.fixture
def sara_id(client, sara, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "sara@example.com").first().id


@pytest.fixture
def ali_id(client, ali, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "ali@example.com").first().id


# --- when the case is created ---

def test_creating_a_case_with_an_assignee_records_who_did_it(
    client, ali, ali_client_id, sara_id
):
    body = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Work for Sara",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    ).json()

    assert body["last_assignment"]["assignee"]["name"] == "Sara Sheikh"
    assert body["last_assignment"]["assigned_by"]["name"] == "Ali Khan"


def test_a_case_with_no_assignee_has_no_history(client, ali, ali_case_id):
    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert body["last_assignment"] is None
    assert body["assignments"] == []


# --- badalte waqt ---

def test_changing_the_assignee_adds_a_row_and_keeps_the_old_one(
    client, ali, ali_case_id, sara_id, ali_id
):
    client.patch(f"/cases/{ali_case_id}", json={"assignee_id": sara_id}, headers=ali)
    client.patch(f"/cases/{ali_case_id}", json={"assignee_id": ali_id}, headers=ali)

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    # Newest first, nothing overwritten.
    assert [a["assignee"]["name"] for a in body["assignments"]] == [
        "Ali Khan",
        "Sara Sheikh",
    ]
    assert body["last_assignment"]["assignee"]["name"] == "Ali Khan"


def test_setting_the_same_assignee_again_records_nothing(
    client, ali, ali_case_id, sara_id
):
    for _ in range(2):
        client.patch(
            f"/cases/{ali_case_id}", json={"assignee_id": sara_id}, headers=ali
        )

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert len(body["assignments"]) == 1


def test_removing_the_assignee_is_recorded_too(client, ali, ali_case_id, sara_id):
    client.patch(f"/cases/{ali_case_id}", json={"assignee_id": sara_id}, headers=ali)
    client.patch(f"/cases/{ali_case_id}", json={"assignee_id": None}, headers=ali)

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert len(body["assignments"]) == 2
    # Unassigning is an event too: someone did it, nobody received it.
    assert body["assignments"][0]["assignee"] is None
    assert body["assignments"][0]["assigned_by"]["name"] == "Ali Khan"


def test_editing_the_title_does_not_touch_the_history(client, ali, ali_case_id):
    client.patch(f"/cases/{ali_case_id}", json={"title": "Naya naam"}, headers=ali)

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert body["assignments"] == []


# --- list endpoint ---

def test_the_cases_list_carries_the_last_assignment(
    client, ali, ali_client_id, sara_id
):
    client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Work for Sara",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    )

    row = client.get("/cases", headers=ali).json()["items"][0]

    assert row["last_assignment"]["assigned_by"]["name"] == "Ali Khan"


def test_the_assignee_also_sees_who_assigned_it(client, ali, sara, ali_client_id, sara_id):
    client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Work for Sara",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    )

    row = client.get("/cases", headers=sara).json()["items"][0]

    assert row["last_assignment"]["assigned_by"]["name"] == "Ali Khan"


def test_a_removed_staff_member_cannot_be_assigned_on_create(client, ali, admin, ali_client_id):
    # A removed account is gone from /staff, so it must not be reachable as an
    # assignee either - otherwise the case shows someone nobody can pick.
    staff = client.post(
        "/auth/register",
        json={"name": "Leaver", "email": "leaver@example.com", "password": "password123"},
        headers=admin,
    ).json()
    client.delete(f"/staff/{staff['id']}", headers=admin)

    response = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Ghost case",
            "case_type": "Civil",
            "assignee_id": staff["id"],
        },
        headers=ali,
    )
    assert response.status_code == 404


def test_a_removed_staff_member_cannot_be_assigned_on_update(client, ali, admin, ali_case_id):
    staff = client.post(
        "/auth/register",
        json={"name": "Leaver2", "email": "leaver2@example.com", "password": "password123"},
        headers=admin,
    ).json()
    client.delete(f"/staff/{staff['id']}", headers=admin)

    response = client.patch(
        f"/cases/{ali_case_id}", json={"assignee_id": staff["id"]}, headers=ali
    )
    assert response.status_code == 404


def test_a_case_can_still_be_unassigned(client, ali, sara, ali_client_id):
    # Sending null is how an assignee is removed. There is nobody to look up,
    # so the check above must not run for it.
    sara_id = client.get("/me", headers=sara).json()["id"]
    case_id = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Assigned then not",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    ).json()["id"]

    response = client.patch(f"/cases/{case_id}", json={"assignee_id": None}, headers=ali)
    assert response.status_code == 200
    assert response.json()["assignee"] is None
