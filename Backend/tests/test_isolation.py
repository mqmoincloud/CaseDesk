"""Epic 5 - ownership isolation and deletion integrity (US-15, US-16).

US-15 says to verify by signing in as one user and calling every endpoint with
the other's ids. That is what these tests do.
"""

import pytest


@pytest.fixture
def sara_data(client, sara):
    """A client, a case and a note that all belong to Sara."""
    client_id = client.post(
        "/clients/registration",
        json={"name": "Sara Client", "email": "sara.client@example.com", "phone": "5550001"},
        headers=sara,
    ).json()["id"]
    case_id = client.post(
        "/cases/registration",
        json={"client_id": client_id, "title": "Sara Case", "case_type": "Family"},
        headers=sara,
    ).json()["id"]
    note_id = client.post(
        f"/cases/{case_id}/notes", json={"body": "Sara private note"}, headers=sara
    ).json()["id"]
    return {"client_id": client_id, "case_id": case_id, "note_id": note_id}


def test_ali_sees_none_of_saras_records(client, ali, sara_data):
    assert client.get("/clients", headers=ali).json()["total"] == 0
    assert client.get("/cases", headers=ali).json()["total"] == 0


def test_reading_another_users_records_returns_404(client, ali, sara_data):
    # 404 and not 403: a 403 would confirm the record exists, which is the leak.
    assert client.get(f"/clients/{sara_data['client_id']}", headers=ali).status_code == 404
    assert client.get(f"/cases/{sara_data['case_id']}", headers=ali).status_code == 404


def test_writing_to_another_users_records_returns_404(client, ali, sara_data):
    # US-15: the rule covers update and delete, not only read.
    assert client.patch(
        f"/clients/{sara_data['client_id']}", json={"name": "Hacked"}, headers=ali
    ).status_code == 404
    assert client.delete(f"/clients/{sara_data['client_id']}", headers=ali).status_code == 404
    assert client.patch(
        f"/cases/{sara_data['case_id']}", json={"title": "Hacked"}, headers=ali
    ).status_code == 404
    assert client.patch(
        f"/cases/{sara_data['case_id']}/status", json={"status": "Active"}, headers=ali
    ).status_code == 404
    assert client.post(
        f"/cases/{sara_data['case_id']}/notes", json={"body": "Hacked"}, headers=ali
    ).status_code == 404
    assert client.delete(f"/notes/{sara_data['note_id']}", headers=ali).status_code == 404


def test_search_does_not_reach_across_users(client, ali, sara_data):
    # US-15 calls this out specifically: search is the endpoint people forget.
    assert client.get("/clients?search=Sara Client", headers=ali).json()["total"] == 0
    assert client.get("/clients?search=sara.client@example.com", headers=ali).json()["total"] == 0
    assert client.get("/clients?search=5550001", headers=ali).json()["total"] == 0


# --- US-16: a deleted client must vanish from every one of these ---

def test_deleted_client_is_gone_from_the_list(client, ali, ali_client_id):
    client.delete(f"/clients/{ali_client_id}", headers=ali)
    assert client.get("/clients", headers=ali).json()["items"] == []


def test_deleted_client_is_gone_from_search(client, ali, ali_client_id):
    client.delete(f"/clients/{ali_client_id}", headers=ali)
    assert client.get("/clients?search=Ramesh", headers=ali).json()["total"] == 0


def test_deleted_client_is_gone_from_the_total(client, ali, ali_client_id):
    client.post("/clients/registration", json={"name": "Survivor"}, headers=ali)
    client.delete(f"/clients/{ali_client_id}", headers=ali)
    assert client.get("/clients", headers=ali).json()["total"] == 1


def test_deleted_client_id_is_rejected_when_opening_a_case(client, ali, ali_client_id):
    client.delete(f"/clients/{ali_client_id}", headers=ali)
    response = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "Too late", "case_type": "Civil"},
        headers=ali,
    )
    assert response.status_code == 404


def test_the_staff_picker_does_not_hand_out_email_addresses(client, ali):
    # /staff fills the assignee dropdown, which needs a name and an id. It
    # used to send every colleague's email to every logged-in user.
    body = client.get("/staff", headers=ali).json()

    assert body
    for person in body:
        assert set(person.keys()) == {"id", "name"}


def test_an_assignee_is_not_shown_the_owners_email(client, ali, sara, ali_client_id):
    # An assignee can see the case but not the client behind it. The owner and
    # assignee blocks used to carry email addresses along for the ride.
    sara_id = client.get("/me", headers=sara).json()["id"]
    client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Shared",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    )

    row = client.get("/cases", headers=sara).json()["items"][0]

    assert set(row["owner"].keys()) == {"id", "name"}
    assert set(row["assignee"].keys()) == {"id", "name"}


def test_only_an_admin_can_read_the_full_staff_list(client, ali, admin):
    assert client.get("/admin/staff", headers=ali).status_code == 403

    body = client.get("/admin/staff", headers=admin).json()
    assert "email" in body[0]
    assert "password_hash" not in body[0]
