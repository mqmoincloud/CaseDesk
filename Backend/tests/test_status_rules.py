"""Epic 6 - case status lifecycle (US-18) and deleting a client with cases (US-19)."""

import pytest


def move(client, headers, case_id, status):
    return client.patch(f"/cases/{case_id}/status", json={"status": status}, headers=headers)


def test_the_whole_allowed_path_works(client, ali, ali_case_id):
    for status in ["Active", "Settled", "Closed"]:
        response = move(client, ali, ali_case_id, status)
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize("target", ["Settled", "Closed"])
def test_skipping_a_step_from_intake_returns_409(client, ali, ali_case_id, target):
    assert move(client, ali, ali_case_id, target).status_code == 409


def test_skipping_a_step_from_active_returns_409(client, ali, ali_case_id):
    move(client, ali, ali_case_id, "Active")
    assert move(client, ali, ali_case_id, "Closed").status_code == 409


def test_going_backwards_returns_409(client, ali, ali_case_id):
    move(client, ali, ali_case_id, "Active")
    assert move(client, ali, ali_case_id, "Intake").status_code == 409


def test_closed_is_terminal(client, ali, ali_case_id):
    for status in ["Active", "Settled", "Closed"]:
        move(client, ali, ali_case_id, status)

    # US-18: a closed case cannot be reopened, by any route back in.
    for status in ["Intake", "Active", "Settled"]:
        assert move(client, ali, ali_case_id, status).status_code == 409


def test_a_rejected_transition_leaves_the_status_untouched(client, ali, ali_case_id):
    move(client, ali, ali_case_id, "Closed")
    assert client.get(f"/cases/{ali_case_id}", headers=ali).json()["status"] == "Intake"


def test_closed_case_drops_out_of_the_active_list(client, ali, ali_case_id):
    # US-12: closing is what takes a case off the active list.
    for status in ["Active", "Settled", "Closed"]:
        move(client, ali, ali_case_id, status)

    assert client.get("/cases?status=Closed", headers=ali).json()["total"] == 1
    assert client.get("/cases?status=Active", headers=ali).json()["total"] == 0


# --- US-19: deleting a client who has cases. This project blocks with 409. ---

def test_deleting_a_client_with_a_live_case_returns_409(client, ali, ali_client_id, ali_case_id):
    assert client.delete(f"/clients/{ali_client_id}", headers=ali).status_code == 409


def test_the_blocked_client_is_still_there_afterwards(client, ali, ali_client_id, ali_case_id):
    client.delete(f"/clients/{ali_client_id}", headers=ali)
    assert client.get(f"/clients/{ali_client_id}", headers=ali).status_code == 200


def test_a_client_with_no_cases_deletes_fine(client, ali, ali_client_id):
    assert client.delete(f"/clients/{ali_client_id}", headers=ali).status_code == 200


def test_a_status_that_does_not_exist_is_a_422(client, ali, ali_case_id):
    # "Banana" is not a status at all, so it is a bad value in the request -
    # 422. 409 is for a real status that is not allowed from here.
    response = client.patch(
        f"/cases/{ali_case_id}/status", json={"status": "Banana"}, headers=ali
    )
    assert response.status_code == 422
    assert "status" in response.json()["error"]["fields"]


# --- a closed case takes no work at all, not just no notes ---


def close(client, headers, case_id):
    for status in ["Active", "Settled", "Closed"]:
        client.patch(f"/cases/{case_id}/status", json={"status": status}, headers=headers)


def test_a_closed_case_cannot_have_its_title_changed(client, ali, ali_case_id):
    close(client, ali, ali_case_id)

    response = client.patch(f"/cases/{ali_case_id}", json={"title": "Naya"}, headers=ali)

    assert response.status_code == 409
    assert client.get(f"/cases/{ali_case_id}", headers=ali).json()["title"] == "Property dispute"


def test_a_closed_case_cannot_be_handed_to_someone_new(client, ali, sara, db, ali_case_id):
    """Band case pe note likhna mana tha par use kisi naye bande ko de dena
    khula tha - yaani band case ko kaam dena aasan aur uspe kaam likhna mana."""
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id
    close(client, ali, ali_case_id)

    response = client.patch(f"/cases/{ali_case_id}", json={"assignee_id": sara_id}, headers=ali)

    assert response.status_code == 409


# --- soft-deleting a case, and deleting the client afterwards ---


def test_deleting_a_case_is_soft(client, ali, ali_case_id):
    assert client.delete(f"/cases/{ali_case_id}", headers=ali).status_code == 200

    # The row is still there, just unreachable by every route.
    assert client.get(f"/cases/{ali_case_id}", headers=ali).status_code == 404
    assert client.get("/cases", headers=ali).json()["total"] == 0


def test_a_client_can_be_deleted_once_their_cases_are_gone(client, ali, ali_client_id, ali_case_id):
    """There was no delete-case route, so any client with even one case could
    never be removed - US-07 was unreachable."""
    assert client.delete(f"/clients/{ali_client_id}", headers=ali).status_code == 409

    client.delete(f"/cases/{ali_case_id}", headers=ali)

    assert client.delete(f"/clients/{ali_client_id}", headers=ali).status_code == 200


def test_an_assignee_cannot_delete_the_case(client, ali, sara, db, ali_client_id):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id
    case = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "T", "case_type": "Civil", "assignee_id": sara_id},
        headers=ali,
    ).json()

    assert client.delete(f"/cases/{case['id']}", headers=sara).status_code == 404
