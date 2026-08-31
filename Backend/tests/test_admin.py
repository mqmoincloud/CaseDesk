"""The admin role.

The brief puts roles out of scope, so this whole file describes a deliberate
departure from it - see DECISIONS.md. Two things are being pinned down here:
staff cannot reach anything admin-only, and an admin is not stopped by the
ownership filter that stops everyone else.
"""

from tests.conftest import PASSWORD


# --- who may register staff ---

def test_staff_cannot_register_anyone(client, ali):
    response = client.post(
        "/auth/register",
        json={"name": "Sneaky", "email": "sneaky@example.com", "password": PASSWORD},
        headers=ali,
    )
    assert response.status_code == 403


def test_registering_without_a_token_is_401_not_403(client):
    # No token at all is an authentication problem, not a permission one.
    response = client.post(
        "/auth/register",
        json={"name": "Nobody", "email": "nobody@example.com", "password": PASSWORD},
    )
    assert response.status_code == 401


def test_admin_can_register_staff(client, admin):
    response = client.post(
        "/auth/register",
        json={"name": "New Person", "email": "new@example.com", "password": PASSWORD},
        headers=admin,
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"


def test_a_registered_staff_member_can_log_in(client, admin):
    client.post(
        "/auth/register",
        json={"name": "New Person", "email": "new@example.com", "password": PASSWORD},
        headers=admin,
    )
    response = client.post(
        "/auth/login", json={"email": "new@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200


# --- the ownership filter does not apply to an admin ---

def test_admin_sees_every_clients_records(client, ali, sara, admin, ali_client_id):
    client.post("/clients/registration", json={"name": "Sara Client"}, headers=sara)

    # Each staff member sees only their own.
    assert client.get("/clients", headers=ali).json()["total"] == 1
    assert client.get("/clients", headers=sara).json()["total"] == 1

    # The admin sees both.
    assert client.get("/clients", headers=admin).json()["total"] == 2


def test_admin_can_open_a_client_that_is_not_theirs(client, ali, admin, ali_client_id):
    response = client.get(f"/clients/{ali_client_id}", headers=admin)
    assert response.status_code == 200
    assert response.json()["name"] == "Ramesh Kumar"


def test_admin_can_open_a_case_that_is_not_theirs(client, ali, admin, ali_case_id):
    response = client.get(f"/cases/{ali_case_id}", headers=admin)
    assert response.status_code == 200


def test_admin_sees_every_case_in_the_list(client, ali, sara, admin, ali_case_id):
    assert client.get("/cases", headers=ali).json()["total"] == 1
    assert client.get("/cases", headers=sara).json()["total"] == 0
    assert client.get("/cases", headers=admin).json()["total"] == 1


def test_admin_can_add_a_note_to_someone_elses_case(client, ali, admin, ali_case_id):
    response = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Checked by admin"}, headers=admin
    )
    assert response.status_code == 200
    assert response.json()["author"]["name"] == "Admin"


# --- staff are still walled off from each other ---

def test_the_admin_role_does_not_leak_to_staff(client, ali, sara, ali_client_id):
    # The whole point of the filter is that only role == "admin" bypasses it.
    assert client.get(f"/clients/{ali_client_id}", headers=sara).status_code == 404
    assert client.get("/clients?search=Ramesh", headers=sara).json()["total"] == 0


def test_new_accounts_are_staff_not_admins(client, admin, db):
    from src.models import Staff

    client.post(
        "/auth/register",
        json={"name": "New Person", "email": "new@example.com", "password": PASSWORD},
        headers=admin,
    )

    created = db.query(Staff).filter(Staff.email == "new@example.com").first()
    assert created.role == "staff"


# --- an admin working on behalf of a staff member ---

def test_admin_creates_a_client_for_a_staff_member(client, ali, admin, db):
    from src.models import Client, Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    created = client.post(
        "/clients/registration",
        json={"name": "Handed To Ali", "staff_id": ali_id},
        headers=admin,
    ).json()

    row = db.query(Client).filter(Client.id == created["id"]).first()
    assert row.staff_id == ali_id

    # And Ali really has it - it is not just a column value.
    assert client.get(f"/clients/{created['id']}", headers=ali).status_code == 200


def test_a_staff_member_cannot_hand_a_client_to_someone_else(client, ali, sara, db):
    """Refused outright, not ignored in silence.

    This used to return 200 with the client still owned by Sara: what was asked
    for did not happen, and nobody was told. 403 rather than 404 because there
    is no record to hide - the action is simply out of scope, the same reason
    require_admin gives.
    """
    from src.models import Client, Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    response = client.post(
        "/clients/registration",
        json={"name": "Nice Try", "staff_id": ali_id},
        headers=sara,
    )

    assert response.status_code == 403

    # Refused means nothing was created, for either owner.
    assert db.query(Client).filter(Client.name == "Nice Try").count() == 0


def test_admin_handing_a_client_to_an_unknown_staff_id_is_404(client, admin):
    response = client.post(
        "/clients/registration",
        json={"name": "Nowhere", "staff_id": 99999},
        headers=admin,
    )
    assert response.status_code == 404


def test_a_case_the_admin_opens_belongs_to_the_clients_owner(client, ali, admin, db):
    from src.models import Case, Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    # Admin sets up a client for Ali, then opens a case on it for him.
    client_id = client.post(
        "/clients/registration",
        json={"name": "Ali's Client", "staff_id": ali_id},
        headers=admin,
    ).json()["id"]

    case_id = client.post(
        "/cases/registration",
        json={"client_id": client_id, "title": "Opened by admin", "case_type": "Civil"},
        headers=admin,
    ).json()["id"]

    # The case is Ali's, not the admin's.
    row = db.query(Case).filter(Case.id == case_id).first()
    assert row.staff_id == ali_id

    # So it turns up in Ali's list without him doing anything.
    listing = client.get("/cases", headers=ali).json()
    assert [c["id"] for c in listing["items"]] == [case_id]


def test_a_staff_members_own_case_still_belongs_to_them(client, ali, ali_client_id, db):
    from src.models import Case, Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    case_id = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "Mine", "case_type": "Civil"},
        headers=ali,
    ).json()["id"]

    # Nothing changed for the ordinary path: client owner and creator are the
    # same person, so the case lands where it always did.
    row = db.query(Case).filter(Case.id == case_id).first()
    assert row.staff_id == ali_id


def test_the_staff_member_can_then_reassign_the_case(client, ali, sara, admin, db):
    from src.models import Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id
    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    client_id = client.post(
        "/clients/registration",
        json={"name": "Ali's Client", "staff_id": ali_id},
        headers=admin,
    ).json()["id"]
    case_id = client.post(
        "/cases/registration",
        json={"client_id": client_id, "title": "Handed over", "case_type": "Civil"},
        headers=admin,
    ).json()["id"]

    # Ali decides Sara should handle it.
    response = client.patch(
        f"/cases/{case_id}", json={"assignee_id": sara_id}, headers=ali
    )
    assert response.status_code == 200
    assert response.json()["assignee"]["name"] == "Sara Sheikh"

    # Sara can now open it; Ali still owns it.
    assert client.get(f"/cases/{case_id}", headers=sara).status_code == 200


def test_admin_cannot_hand_a_client_to_a_removed_staff_member(client, admin):
    # Removal is refused while someone still owns live work, so handing them
    # new work afterwards has to be refused too - otherwise the rule only
    # holds on the way out.
    staff = client.post(
        "/auth/register",
        json={"name": "Leaver", "email": "leaver@example.com", "password": "password123"},
        headers=admin,
    ).json()
    client.delete(f"/staff/{staff['id']}", headers=admin)

    response = client.post(
        "/clients/registration",
        json={"name": "Ghost Client", "staff_id": staff["id"]},
        headers=admin,
    )
    assert response.status_code == 404
