"""Epic 2 - clients (US-04 to US-08)."""


def test_create_client_sets_timestamps(client, ali):
    response = client.post(
        "/clients/registration",
        json={"name": "Ramesh", "email": "r@example.com", "phone": "9876543210", "address": "Delhi"},
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


def test_a_badly_formatted_phone_is_rejected(client, ali):
    # US-04 - phone is format-validated. The rule lives on the schema, so the
    # error names the field the same way every other validation error does.
    response = client.post(
        "/clients/registration",
        json={"name": "Bad Phone", "phone": "not-a-phone!!!"},
        headers=ali,
    )
    assert response.status_code == 422
    assert "phone" in response.json()["error"]["fields"]


def test_a_badly_formatted_phone_is_rejected_on_update_too(client, ali, ali_client_id):
    # Validating only on create would let a bad number in through PATCH.
    response = client.patch(
        f"/clients/{ali_client_id}", json={"phone": "nope"}, headers=ali
    )
    assert response.status_code == 422
    assert "phone" in response.json()["error"]["fields"]


def test_sending_name_as_null_is_a_422_not_a_500(client, ali, ali_client_id):
    # name is NOT NULL in the database. Leaving it out of a PATCH is fine;
    # sending it as null used to reach the database and come back as a 500.
    response = client.patch(f"/clients/{ali_client_id}", json={"name": None}, headers=ali)
    assert response.status_code == 422
    assert "name" in response.json()["error"]["fields"]


def test_nullable_fields_can_still_be_cleared(client, ali, ali_client_id):
    # email, phone and address are nullable columns, so null is a real
    # instruction there - it clears the field.
    response = client.patch(f"/clients/{ali_client_id}", json={"email": None}, headers=ali)
    assert response.status_code == 200
    assert response.json()["email"] is None


def test_search_treats_a_percent_sign_as_text(client, ali):
    # % is a wildcard in LIKE. Unescaped, searching for it matched every row.
    client.post("/clients/registration", json={"name": "Plain Name"}, headers=ali)
    assert client.get("/clients?search=%25", headers=ali).json()["total"] == 0

    client.post("/clients/registration", json={"name": "100% Sure"}, headers=ali)
    assert client.get("/clients?search=%25", headers=ali).json()["total"] == 1


def test_search_treats_an_underscore_as_text(client, ali):
    # _ matches any single character in LIKE.
    client.post("/clients/registration", json={"name": "abc"}, headers=ali)
    assert client.get("/clients?search=a_c", headers=ali).json()["total"] == 0


# --- a client's owner has to come back in the response ---


def test_a_client_carries_its_owner(client, ali, ali_client_id):
    """An admin's list holds everyone's clients. Without this field it could
    not say which client belonged to whom."""
    body = client.get(f"/clients/{ali_client_id}", headers=ali).json()

    assert body["owner"]["name"] == "Ali Khan"
    # Id and name only - no reason to put a colleague's email on screen.
    assert set(body["owner"].keys()) == {"id", "name"}


def test_the_admin_sees_who_each_client_belongs_to(client, admin, ali, ali_client_id):
    rows = client.get("/clients", headers=admin).json()["items"]
    owners = {row["owner"]["name"] for row in rows}

    assert owners == {"Ali Khan"}


def test_email_is_lowercased_on_update_too(client, ali, ali_client_id):
    """Create lowercased the address and update did not, so one field was
    stored two different ways."""
    client.patch(f"/clients/{ali_client_id}", json={"email": "R.Kumar@Example.COM"}, headers=ali)

    body = client.get(f"/clients/{ali_client_id}", headers=ali).json()
    assert body["email"] == "r.kumar@example.com"
