"""Filters on the cases list, alone and in combination.

The combining tests are the point. With each filter in its own if, the easiest
mistake is one quietly replacing another, and that only shows when two are
applied together.
"""

import pytest


@pytest.fixture
def sara_id(client, sara, db):
    from src.models import Staff

    return db.query(Staff).filter(Staff.email == "sara@example.com").first().id


@pytest.fixture
def two_clients(client, ali):
    ids = []
    for name in ["Ramesh Kumar", "Sunita Patel"]:
        ids.append(
            client.post(
                "/clients/registration", json={"name": name}, headers=ali
            ).json()["id"]
        )
    return ids


@pytest.fixture
def cases(client, ali, two_clients, sara_id):
    """Four cases, so every filter has something to exclude."""
    ramesh, sunita = two_clients
    made = []
    for client_id, title, case_type, assignee_id in [
        (ramesh, "Property dispute", "Civil", sara_id),
        (ramesh, "Tenancy notice", "Civil", None),
        (sunita, "Property dispute", "Criminal", sara_id),
        (sunita, "Bail plea", "Criminal", None),
    ]:
        made.append(
            client.post(
                "/cases/registration",
                json={
                    "client_id": client_id,
                    "title": title,
                    "case_type": case_type,
                    "assignee_id": assignee_id,
                },
                headers=ali,
            ).json()["id"]
        )
    return made


def titles(body):
    return sorted(row["title"] for row in body["items"])


def test_search_matches_the_case_title(client, ali, cases):
    body = client.get("/cases?search=tenancy", headers=ali).json()

    assert titles(body) == ["Tenancy notice"]


def test_search_matches_the_client_name(client, ali, cases):
    body = client.get("/cases?search=sunita", headers=ali).json()

    assert titles(body) == ["Bail plea", "Property dispute"]


def test_search_matches_the_case_type(client, ali, cases):
    body = client.get("/cases?search=criminal", headers=ali).json()

    assert titles(body) == ["Bail plea", "Property dispute"]


def test_search_ignores_case(client, ali, cases):
    assert client.get("/cases?search=RAMESH", headers=ali).json()["total"] == 2


def test_search_that_matches_nothing_is_empty_not_everything(client, ali, cases):
    body = client.get("/cases?search=zzzz", headers=ali).json()

    assert body["total"] == 0
    assert body["items"] == []


def test_the_total_counts_the_filtered_list_not_all_cases(client, ali, cases):
    body = client.get("/cases?search=sunita", headers=ali).json()

    # Four cases exist, two survive the filter - total reports what is shown.
    assert body["total"] == 2


def test_search_and_status_work_together(client, ali, cases):
    # Move one of Ramesh's two cases to Active.
    active = client.get("/cases?search=tenancy", headers=ali).json()["items"][0]
    client.patch(f"/cases/{active['id']}/status", json={"status": "Active"}, headers=ali)

    body = client.get("/cases?search=ramesh&status=Active", headers=ali).json()

    assert titles(body) == ["Tenancy notice"]


def test_search_and_assignee_work_together(client, ali, cases, sara_id):
    body = client.get(f"/cases?search=property&assignee={sara_id}", headers=ali).json()

    # Both "Property dispute" cases are Sara's, so here search narrows and the
    # assignee filter does not.
    assert body["total"] == 2

    body = client.get(f"/cases?search=bail&assignee={sara_id}", headers=ali).json()

    # Bail plea is unassigned, so the two filters together return nothing.
    assert body["total"] == 0


def test_search_and_client_id_work_together(client, ali, cases, two_clients):
    ramesh, _ = two_clients

    body = client.get(
        f"/cases?search=property&client_id={ramesh}", headers=ali
    ).json()

    # Both clients have a "Property dispute"; client_id keeps only Ramesh's.
    assert titles(body) == ["Property dispute"]
    assert body["items"][0]["client"]["name"] == "Ramesh Kumar"


def test_all_four_filters_at_once(client, ali, cases, two_clients, sara_id):
    ramesh, _ = two_clients

    body = client.get(
        f"/cases?search=property&status=Intake&assignee={sara_id}"
        f"&client_id={ramesh}",
        headers=ali,
    ).json()

    assert titles(body) == ["Property dispute"]
    assert body["total"] == 1


# --- a bad filter value gives one answer, not two ---


def test_a_status_that_does_not_exist_is_a_422_on_the_list_too(client, ali):
    """PATCH /cases/{id}/status pe "Banana" hamesha 422 tha, par list pe wahi
    value 200 aur khaali list deti thi - ek hi galti ke do alag jawab."""
    assert client.get("/cases?status=Banana", headers=ali).status_code == 422


def test_assignee_zero_is_rejected_rather_than_ignored(client, ali, ali_case_id):
    """Python me 0 jhoot ginta hai, to `if assignee:` ise filter hi nahi maanta
    tha: poochha "assignee 0 wale cases", mila "saare cases"."""
    assert client.get("/cases?assignee=0", headers=ali).status_code == 422
    assert client.get("/cases?client_id=0", headers=ali).status_code == 422


def test_an_assignee_nobody_has_returns_an_empty_list_not_everything(client, ali, ali_case_id):
    body = client.get("/cases?assignee=9999", headers=ali).json()
    assert body["total"] == 0
