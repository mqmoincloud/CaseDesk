"""What an assignee can and cannot do with a case that is not theirs.

US-15 says a staff member's cases are invisible to everyone else. US-11 wants
cases filtered by assignee "so I can see what is on my plate" - which is empty
if the person a case is assigned to cannot open it. We widened US-15 just far
enough to close that hole: an assignee can read the case and add notes to it,
and nothing more. These tests pin down both halves of that.
"""

import pytest

from tests.conftest import register_and_login


@pytest.fixture
def sara_id(client, sara, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "sara@example.com").first().id


@pytest.fixture
def assigned_case(client, ali, ali_client_id, sara_id):
    """A case Ali owns, assigned to Sara."""
    return client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Work for Sara",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    ).json()["id"]


# --- what the assignee gains ---

def test_assignee_can_open_the_case(client, sara, assigned_case):
    response = client.get(f"/cases/{assigned_case}", headers=sara)

    assert response.status_code == 200
    assert response.json()["title"] == "Work for Sara"


def test_the_case_shows_up_in_the_assignees_list(client, sara, assigned_case):
    body = client.get("/cases", headers=sara).json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == assigned_case


def test_assignee_can_add_a_note(client, sara, assigned_case):
    response = client.post(
        f"/cases/{assigned_case}/notes", json={"body": "Looked into it"}, headers=sara
    )

    assert response.status_code == 200
    assert response.json()["author"]["name"] == "Sara Sheikh"


def test_assignee_can_read_notes_the_owner_wrote(client, ali, sara, assigned_case):
    client.post(f"/cases/{assigned_case}/notes", json={"body": "From Ali"}, headers=ali)

    notes = client.get(f"/cases/{assigned_case}", headers=sara).json()["notes"]
    assert [note["body"] for note in notes] == ["From Ali"]


# --- what stays with the owner ---

def test_assignee_cannot_edit_the_case(client, sara, assigned_case):
    response = client.patch(
        f"/cases/{assigned_case}", json={"title": "Renamed"}, headers=sara
    )
    assert response.status_code == 404


def test_assignee_cannot_move_the_status(client, sara, assigned_case):
    response = client.patch(
        f"/cases/{assigned_case}/status", json={"status": "Active"}, headers=sara
    )
    assert response.status_code == 404


def test_assignee_cannot_reassign_the_case_away(client, sara, sara_id, assigned_case):
    response = client.patch(
        f"/cases/{assigned_case}", json={"assignee_id": sara_id}, headers=sara
    )
    assert response.status_code == 404


def test_assignee_cannot_delete_a_note(client, ali, sara, assigned_case):
    note_id = client.post(
        f"/cases/{assigned_case}/notes", json={"body": "Ali's note"}, headers=ali
    ).json()["id"]

    # US-14 is unchanged: only notes on cases I own.
    assert client.delete(f"/notes/{note_id}", headers=sara).status_code == 404


def test_assignee_cannot_reach_the_client_behind_the_case(client, sara, ali_client_id, assigned_case):
    # The case detail shows the client's name, but the client record itself
    # still belongs to the owner alone.
    assert client.get(f"/clients/{ali_client_id}", headers=sara).status_code == 404
    assert client.get("/clients", headers=sara).json()["total"] == 0


# --- everyone else is still shut out ---

def test_a_third_staff_member_still_sees_nothing(client, ali, sara, admin, assigned_case):
    raj = register_and_login(client, "Raj Mehta", "raj@example.com", admin)

    assert client.get(f"/cases/{assigned_case}", headers=raj).status_code == 404
    assert client.get("/cases", headers=raj).json()["total"] == 0
    assert client.post(
        f"/cases/{assigned_case}/notes", json={"body": "nope"}, headers=raj
    ).status_code == 404


def test_unassigning_takes_the_case_away_again(client, ali, sara, assigned_case):
    assert client.get(f"/cases/{assigned_case}", headers=sara).status_code == 200

    client.patch(f"/cases/{assigned_case}", json={"assignee_id": None}, headers=ali)

    assert client.get(f"/cases/{assigned_case}", headers=sara).status_code == 404


def test_the_case_says_who_owns_it(client, ali, sara, assigned_case):
    """The UI needs this to decide what to render for an assignee.

    Without an owner on the response the frontend cannot tell "this is mine"
    from "I am only assigned to it", and would have to offer every control and
    let the API reject half of them.
    """
    body = client.get(f"/cases/{assigned_case}", headers=sara).json()

    assert body["owner"]["name"] == "Ali Khan"
    assert body["assignee"]["name"] == "Sara Sheikh"


def test_the_owner_is_on_the_list_rows_too(client, ali, assigned_case):
    row = client.get("/cases", headers=ali).json()["items"][0]
    assert row["owner"]["name"] == "Ali Khan"
