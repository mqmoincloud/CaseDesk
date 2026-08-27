"""Epic 3 - cases (US-09 to US-12)."""


def test_new_case_starts_at_intake(client, ali, ali_client_id):
    response = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "Dispute", "case_type": "Civil"},
        headers=ali,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Intake"
    assert response.json()["version"] == 1


def test_status_in_the_body_is_ignored(client, ali, ali_client_id):
    # US-09 + US-18: the caller must not be able to pick a starting status,
    # or the whole lifecycle can be skipped at creation time.
    response = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Sneaky",
            "case_type": "Civil",
            "status": "Closed",
        },
        headers=ali,
    )
    assert response.json()["status"] == "Intake"


def test_case_on_another_staffs_client_returns_404(client, ali, sara):
    sara_client = client.post(
        "/clients/registration", json={"name": "Sara Client"}, headers=sara
    ).json()["id"]

    response = client.post(
        "/cases/registration",
        json={"client_id": sara_client, "title": "Steal", "case_type": "Civil"},
        headers=ali,
    )
    assert response.status_code == 404


def test_case_on_a_soft_deleted_client_is_rejected(client, ali, ali_client_id):
    # US-16, sixth point: a deleted client's id must be refused here too.
    client.delete(f"/clients/{ali_client_id}", headers=ali)

    response = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "Too late", "case_type": "Civil"},
        headers=ali,
    )
    assert response.status_code == 404


def test_unknown_assignee_returns_404_not_500(client, ali, ali_client_id):
    response = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Bad assignee",
            "case_type": "Civil",
            "assignee_id": 99999,
        },
        headers=ali,
    )
    assert response.status_code == 404


def test_case_can_be_assigned_to_another_staff_member(client, ali, sara, ali_client_id, db):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    response = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Shared work",
            "case_type": "Civil",
            "assignee_id": sara_id,
        },
        headers=ali,
    )
    assert response.status_code == 200
    assert response.json()["assignee"]["name"] == "Sara Sheikh"


def test_case_detail_shows_client_and_notes(client, ali, ali_case_id):
    client.post(f"/cases/{ali_case_id}/notes", json={"body": "First note"}, headers=ali)

    response = client.get(f"/cases/{ali_case_id}", headers=ali)
    assert response.status_code == 200
    body = response.json()
    assert body["client"]["name"] == "Ramesh Kumar"
    assert len(body["notes"]) == 1


def test_unassigned_case_is_still_visible_to_its_owner(client, ali, ali_case_id):
    # Ownership is staff_id, not assignee_id - filtering on the wrong column
    # would hide every unassigned case from the person who created it.
    response = client.get(f"/cases/{ali_case_id}", headers=ali)
    assert response.status_code == 200
    assert response.json()["assignee"] is None


def test_partial_update_leaves_other_fields_alone(client, ali, ali_case_id):
    response = client.patch(
        f"/cases/{ali_case_id}", json={"title": "Renamed"}, headers=ali
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert response.json()["case_type"] == "Civil"


def test_status_cannot_be_changed_through_the_general_update(client, ali, ali_case_id):
    # US-18 has to hold for any caller, so the plain PATCH must not be a way round it.
    response = client.patch(
        f"/cases/{ali_case_id}", json={"status": "Closed"}, headers=ali
    )
    assert response.json()["status"] == "Intake"


def test_list_shows_client_name_and_assignee_name(client, ali, ali_case_id):
    # US-11 asks for names in the list, not bare ids.
    body = client.get("/cases", headers=ali).json()
    row = body["items"][0]
    assert row["client"]["name"] == "Ramesh Kumar"
    assert "assignee" in row


def test_status_and_assignee_filters_combine(client, ali, ali_client_id, sara, db):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    def make(title, assignee_id):
        return client.post(
            "/cases/registration",
            json={
                "client_id": ali_client_id,
                "title": title,
                "case_type": "Civil",
                "assignee_id": assignee_id,
            },
            headers=ali,
        ).json()["id"]

    unassigned = make("A", None)
    assigned = make("B", sara_id)
    client.patch(f"/cases/{assigned}/status", json={"status": "Active"}, headers=ali)

    assert client.get("/cases", headers=ali).json()["total"] == 2
    assert client.get("/cases?status=Active", headers=ali).json()["total"] == 1
    assert client.get(f"/cases?assignee={sara_id}", headers=ali).json()["total"] == 1

    # Both filters together must narrow to the intersection, not replace each other.
    both = client.get(f"/cases?status=Intake&assignee={sara_id}", headers=ali).json()
    assert both["total"] == 0


def test_cases_can_be_filtered_by_client(client, ali, ali_client_id, ali_case_id):
    other_client = client.post(
        "/clients/registration", json={"name": "Other Client"}, headers=ali
    ).json()["id"]
    client.post(
        "/cases/registration",
        json={"client_id": other_client, "title": "Other case", "case_type": "Family"},
        headers=ali,
    )

    assert client.get("/cases", headers=ali).json()["total"] == 2

    filtered = client.get(f"/cases?client_id={ali_client_id}", headers=ali).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["id"] == ali_case_id


def test_client_filter_does_not_reach_across_users(client, ali, sara, ali_client_id, ali_case_id):
    # Passing someone else's client id must not surface their cases.
    assert client.get(f"/cases?client_id={ali_client_id}", headers=sara).json()["total"] == 0
