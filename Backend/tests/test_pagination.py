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
    """Page through everything with the cursor and return the ids in order."""
    collected, cursor = [], None
    while True:
        page_url = f"{url}&limit={limit}"
        if cursor:
            page_url += f"&before={cursor}"

        body = client.get(page_url, headers=headers).json()
        collected.extend(item["id"] for item in body["items"])

        if not body["has_next"]:
            return collected, body
        cursor = body["next_cursor"]


def test_total_counts_every_record(client, ali, many_clients):
    assert client.get("/clients", headers=ali).json()["total"] == TOTAL


def test_walking_every_page_yields_each_record_exactly_once(client, ali, many_clients):
    ids, _ = walk(client, ali, "/clients?", limit=10)
    assert len(ids) == TOTAL
    assert len(set(ids)) == TOTAL


def test_has_next_is_false_only_on_the_last_page(client, ali, many_clients):
    pages, cursor = 0, None
    while True:
        url = "/clients?limit=10" + (f"&before={cursor}" if cursor else "")
        body = client.get(url, headers=ali).json()
        pages += 1

        if not body["has_next"]:
            break

        assert body["next_cursor"] is not None, "has_next is true but no cursor to follow"
        cursor = body["next_cursor"]

    assert pages == (TOTAL + 9) // 10


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
    """The list is newest-first, and a write mid-walk still must not disturb it.

    The cursor is what makes this safe. Page two asks for rows *before* the last
    id page one showed, so a client created in between takes a higher id and
    falls outside that window entirely. With offset paging the same insert would
    push every row down one place and page two would repeat a record the caller
    had already seen.
    """
    page_one = client.get("/clients?limit=10", headers=ali).json()

    client.post("/clients/registration", json={"name": "Inserted Midway"}, headers=ali)

    page_two = client.get(
        f"/clients?limit=10&before={page_one['next_cursor']}", headers=ali
    ).json()

    first_ids = {item["id"] for item in page_one["items"]}
    second_ids = {item["id"] for item in page_two["items"]}
    assert first_ids.isdisjoint(second_ids)

    # The new client is not silently injected into a page already walked past.
    assert "Inserted Midway" not in [item["name"] for item in page_two["items"]]


def test_a_cursor_past_the_end_returns_an_empty_list_not_an_error(client, ali, many_clients):
    response = client.get("/clients?limit=10&before=1", headers=ali)
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["has_next"] is False
    assert response.json()["next_cursor"] is None


def test_the_newest_record_is_on_the_first_page(client, ali, many_clients):
    newest = client.post(
        "/clients/registration", json={"name": "Just Created"}, headers=ali
    ).json()

    first_page = client.get("/clients?limit=10", headers=ali).json()
    assert first_page["items"][0]["id"] == newest["id"]
    assert first_page["items"][0]["name"] == "Just Created"
