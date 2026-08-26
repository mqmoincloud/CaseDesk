"""Epic 2 - clients (US-04 to US-08)."""


def test_create_client_sets_timestamps(client, ali):
    response = client.post(
        "/clients/registration",
        json={"name": "Ramesh", "email": "r@example.com", "phone": "999", "address": "Delhi"},
        headers=ali,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ramesh"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_only_name_is_required(client, ali):
    # US-04 singles out name; phone and email are validated "when present".
    response = client.post("/clients/registration", json={"name": "OnlyName"}, headers=ali)
    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_missing_name_returns_422(client, ali):
    response = client.post("/clients/registration", json={"email": "x@example.com"}, headers=ali)
    assert response.status_code == 422


def test_malformed_email_returns_422(client, ali):
    response = client.post(
        "/clients/registration", json={"name": "X", "email": "not-an-email"}, headers=ali
    )
    assert response.status_code == 422


def test_email_is_stored_lowercased(client, ali):
    response = client.post(
        "/clients/registration", json={"name": "X", "email": "MiXeD@Example.COM"}, headers=ali
    )
    assert response.json()["email"] == "mixed@example.com"


def test_view_a_client(client, ali, ali_client_id):
    response = client.get(f"/clients/{ali_client_id}", headers=ali)
    assert response.status_code == 200
    assert response.json()["id"] == ali_client_id


def test_unknown_client_returns_404(client, ali):
    assert client.get("/clients/99999", headers=ali).status_code == 404


def test_partial_update_leaves_other_fields_alone(client, ali, ali_client_id):
    # US-06: the fields that weren't sent must survive untouched.
    response = client.patch(
        f"/clients/{ali_client_id}", json={"phone": "1112223333"}, headers=ali
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "1112223333"
    assert body["name"] == "Ramesh Kumar"
    assert body["email"] == "ramesh@example.com"
    assert body["address"] == "1 Main Road, Delhi"


def test_update_changes_updated_at_but_not_created_at(client, ali, ali_client_id):
    before = client.get(f"/clients/{ali_client_id}", headers=ali).json()
    after = client.patch(
        f"/clients/{ali_client_id}", json={"name": "Renamed"}, headers=ali
    ).json()

    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] >= before["updated_at"]


def test_delete_is_soft(client, ali, ali_client_id, db):
    from src.models import Client

    assert client.delete(f"/clients/{ali_client_id}", headers=ali).status_code == 200

    # US-07: the row stays, it just carries a deleted_at now.
    row = db.query(Client).filter(Client.id == ali_client_id).first()
    assert row is not None
    assert row.deleted_at is not None


def test_deleted_client_disappears_from_reads_and_counts(client, ali, ali_client_id):
    client.delete(f"/clients/{ali_client_id}", headers=ali)

    assert client.get(f"/clients/{ali_client_id}", headers=ali).status_code == 404

    listing = client.get("/clients", headers=ali).json()
    assert listing["total"] == 0
    assert listing["items"] == []


def test_search_is_case_insensitive_and_partial(client, ali):
    client.post("/clients/registration", json={"name": "Priya Sharma"}, headers=ali)
    client.post("/clients/registration", json={"name": "Ramesh Kumar"}, headers=ali)

    response = client.get("/clients?search=PRI", headers=ali).json()
    assert response["total"] == 1
    assert response["items"][0]["name"] == "Priya Sharma"


def test_search_matches_phone_and_email(client, ali):
    client.post(
        "/clients/registration",
        json={"name": "Findme", "email": "unique.person@example.com", "phone": "5551234567"},
        headers=ali,
    )

    assert client.get("/clients?search=unique.person", headers=ali).json()["total"] == 1
    assert client.get("/clients?search=5551234", headers=ali).json()["total"] == 1
