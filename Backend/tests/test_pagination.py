"""US-17 - paging, filtering and search that agree with each other.

The brief asks for this to be checked with at least 60 records, a filter
applied, walked from the first page to the last.
"""

import pytest

TOTAL = 65


@pytest.fixture
def many_clients(client, ali):
    for i in range(TOTAL):
        # Half the names carry "Priya" so a filtered walk has something to filter on.
        first = "Priya" if i % 2 == 0 else "Ramesh"
        client.post(
            "/clients/registration",
            json={"name": f"{first} Kumar {i:03d}", "phone": f"98765{i:05d}"},
            headers=ali,
        )
    return TOTAL


def walk(client, headers, url, limit):
    """Page through everything and return the ids, in the order they arrived."""
    collected, page = [], 1
    while True:
        body = client.get(f"{url}&page={page}&limit={limit}", headers=headers).json()
        collected.extend(item["id"] for item in body["items"])
        if not body["has_next"]:
            return collected, body
        page += 1


def test_total_counts_every_record(client, ali, many_clients):
    assert client.get("/clients", headers=ali).json()["total"] == TOTAL


def test_walking_every_page_yields_each_record_exactly_once(client, ali, many_clients):
    ids, _ = walk(client, ali, "/clients?", limit=10)
    assert len(ids) == TOTAL
    assert len(set(ids)) == TOTAL


def test_has_next_is_false_only_on_the_last_page(client, ali, many_clients):
    last_page = (TOTAL + 9) // 10
    for page in range(1, last_page):
        assert client.get(f"/clients?page={page}&limit=10", headers=ali).json()["has_next"] is True
    assert client.get(f"/clients?page={last_page}&limit=10", headers=ali).json()["has_next"] is False


def test_total_reflects_the_filtered_set_not_the_whole_table(client, ali, many_clients):
    # US-17: total is the size of what the filter matched, not of the table.
    filtered = client.get("/clients?search=Priya", headers=ali).json()
    assert filtered["total"] == TOTAL // 2 + 1
    assert filtered["total"] < TOTAL


def test_a_filtered_walk_is_also_complete_and_duplicate_free(client, ali, many_clients):
    ids, _ = walk(client, ali, "/clients?search=Priya", limit=10)
    expected = client.get("/clients?search=Priya", headers=ali).json()["total"]
    assert len(ids) == expected
    assert len(set(ids)) == expected


def test_inserting_while_paging_does_not_duplicate_or_skip(client, ali, many_clients):
    """The ordering has to be stable enough to survive a write mid-walk.

    Ordering ascending by id is what makes this safe: a new row takes the
    highest id and lands at the end, so the pages already visited don't shift.
    Ordering newest-first would push every row down one place and the next page
    would repeat a record the caller had already seen.
    """
    page_one = client.get("/clients?page=1&limit=10", headers=ali).json()

    client.post("/clients/registration", json={"name": "Inserted Midway"}, headers=ali)

    page_two = client.get("/clients?page=2&limit=10", headers=ali).json()

    first_ids = {item["id"] for item in page_one["items"]}
    second_ids = {item["id"] for item in page_two["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_page_beyond_the_end_returns_an_empty_list_not_an_error(client, ali, many_clients):
    response = client.get("/clients?page=99&limit=10", headers=ali)
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["has_next"] is False
