"""What an admin can and cannot do with staff accounts.

Two guards matter most, and both stop an admin locking themselves out: you
cannot change your own role, and you cannot remove your own account. The third
guards the work - someone still holding clients or cases cannot be removed, or
that work would belong to nobody.
"""

import pytest

from tests.conftest import PASSWORD, login


@pytest.fixture
def sara_id(client, sara, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "sara@example.com").first().id


@pytest.fixture
def admin_id(client, admin, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "admin@example.com").first().id


# --- create ---

def test_admin_can_create_a_staff_account(client, admin):
    response = client.post(
        "/auth/register",
        json={"name": "Nadia Rao", "email": "nadia@example.com", "password": PASSWORD},
        headers=admin,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "staff"


def test_admin_can_create_another_admin(client, admin):
    response = client.post(
        "/auth/register",
        json={
            "name": "Second Admin",
            "email": "second@example.com",
            "password": PASSWORD,
            "role": "admin",
        },
        headers=admin,
    )

    assert response.json()["role"] == "admin"

    # And the account really can do admin work. Register is admin-only, so
    # this is the most direct proof the door is open.
    assert client.post(
        "/auth/register",
        json={"name": "Third", "email": "third@example.com", "password": PASSWORD},
        headers=login(client, "second@example.com"),
    ).status_code == 200


def test_a_staff_member_cannot_create_accounts(client, ali):
    response = client.post(
        "/auth/register",
        json={"name": "Nadia Rao", "email": "nadia@example.com", "password": PASSWORD},
        headers=ali,
    )

    assert response.status_code == 403


# --- update ---

def test_admin_can_rename_a_staff_member(client, admin, sara_id):
    response = client.patch(
        f"/staff/{sara_id}", json={"name": "Sara Khan"}, headers=admin
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Sara Khan"


def test_admin_can_promote_someone(client, admin, sara, sara_id):
    client.patch(f"/staff/{sara_id}", json={"role": "admin"}, headers=admin)

    # Being promoted means the admin-only routes now open.
    assert client.post(
        "/auth/register",
        json={"name": "New Hire", "email": "hire@example.com", "password": PASSWORD},
        headers=sara,
    ).status_code == 200


def test_changing_the_password_lets_them_log_in_with_the_new_one(
    client, admin, sara_id
):
    client.patch(f"/staff/{sara_id}", json={"password": "brandnew123"}, headers=admin)

    fresh = client.post(
        "/auth/login", json={"email": "sara@example.com", "password": "brandnew123"}
    )
    stale = client.post(
        "/auth/login", json={"email": "sara@example.com", "password": PASSWORD}
    )

    assert fresh.status_code == 200
    assert stale.status_code == 401


def test_an_email_someone_else_already_has_is_refused(client, admin, ali, sara_id):
    response = client.patch(
        f"/staff/{sara_id}", json={"email": "ali@example.com"}, headers=admin
    )

    assert response.status_code == 409


def test_keeping_your_own_email_is_not_a_clash(client, admin, sara_id):
    response = client.patch(
        f"/staff/{sara_id}", json={"email": "sara@example.com"}, headers=admin
    )

    assert response.status_code == 200


def test_an_admin_cannot_change_their_own_role(client, admin, admin_id):
    response = client.patch(
        f"/staff/{admin_id}", json={"role": "staff"}, headers=admin
    )

    # Otherwise the last admin could demote themselves and lock everyone out.
    assert response.status_code == 409


def test_an_admin_can_still_edit_their_own_name(client, admin, admin_id):
    response = client.patch(f"/staff/{admin_id}", json={"name": "The Boss"}, headers=admin)

    # The block is on the role, not on the whole row.
    assert response.status_code == 200
    assert response.json()["name"] == "The Boss"


def test_a_staff_member_cannot_edit_anyone(client, ali, sara_id):
    response = client.patch(f"/staff/{sara_id}", json={"name": "Nope"}, headers=ali)

    assert response.status_code == 403


# --- delete ---

def test_admin_can_remove_a_staff_member_with_no_work(client, admin, sara, sara_id):
    response = client.delete(f"/staff/{sara_id}", headers=admin)

    assert response.status_code == 200
    # Gone from the list, and their old token stops working.
    assert all(s["id"] != sara_id for s in client.get("/staff", headers=admin).json())
    assert client.get("/me", headers=sara).status_code == 401


def test_a_removed_account_cannot_log_in_again(client, admin, sara_id):
    client.delete(f"/staff/{sara_id}", headers=admin)

    response = client.post(
        "/auth/login", json={"email": "sara@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401


def test_someone_who_owns_a_client_cannot_be_removed(client, admin, ali, ali_client_id, db):
    from src.models import Staff

    ali_id = db.query(Staff).filter(Staff.email == "ali@example.com").first().id

    response = client.delete(f"/staff/{ali_id}", headers=admin)

    assert response.status_code == 409


def test_an_admin_cannot_remove_themselves(client, admin, admin_id):
    response = client.delete(f"/staff/{admin_id}", headers=admin)

    assert response.status_code == 409


def test_a_staff_member_cannot_remove_anyone(client, ali, sara_id):
    assert client.delete(f"/staff/{sara_id}", headers=ali).status_code == 403


def test_removing_the_same_account_twice_is_a_404(client, admin, sara_id):
    client.delete(f"/staff/{sara_id}", headers=admin)

    assert client.delete(f"/staff/{sara_id}", headers=admin).status_code == 404


# --- an assignee's work has to move before they can be removed ---


def test_a_staff_member_who_is_an_assignee_cannot_be_removed(client, admin, ali, sara, db, ali_client_id):
    """The count used to cover what someone owns, not what is assigned to them.

    Sara owns no clients or cases, so she could be removed while Ali's case
    stayed in her name - visible in the list but absent from /staff, which left
    the detail page dropdown blank.
    """
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "T", "case_type": "Civil", "assignee_id": sara_id},
        headers=ali,
    )

    response = client.delete(f"/staff/{sara_id}", headers=admin)

    assert response.status_code == 409
    # And she is still in the picker, because she was not removed.
    names = [s["name"] for s in client.get("/staff", headers=admin).json()]
    assert "Sara Sheikh" in names


def test_once_the_case_is_reassigned_the_removal_goes_through(client, admin, ali, sara, db, ali_client_id):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    case = client.post(
        "/cases/registration",
        json={"client_id": ali_client_id, "title": "T", "case_type": "Civil", "assignee_id": sara_id},
        headers=ali,
    ).json()

    assert client.delete(f"/staff/{sara_id}", headers=admin).status_code == 409

    client.patch(f"/cases/{case['id']}", json={"assignee_id": None}, headers=ali)

    assert client.delete(f"/staff/{sara_id}", headers=admin).status_code == 200
