"""US-21 - a stale update is refused instead of silently overwriting.

Every case row carries a version. A caller that sends the version it was
looking at gets a 409 if the row has moved on since. Sending no version is
still allowed, so the check is opt-in and old callers keep working.
"""


def test_a_new_case_starts_at_version_one(client, ali, ali_case_id):
    assert client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"] == 1


def test_a_successful_update_moves_the_version_on(client, ali, ali_case_id):
    body = client.patch(
        f"/cases/{ali_case_id}", json={"title": "Renamed"}, headers=ali
    ).json()

    assert body["version"] == 2


def test_an_update_carrying_the_current_version_is_accepted(client, ali, ali_case_id):
    current = client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"]

    response = client.patch(
        f"/cases/{ali_case_id}",
        json={"title": "Renamed", "version": current},
        headers=ali,
    )
    assert response.status_code == 200


def test_an_update_carrying_a_stale_version_is_a_409(client, ali, ali_case_id):
    # Two people open the same case, so both are holding version 1.
    first = client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"]
    second = first

    # The first one saves. The row is now at version 2.
    assert client.patch(
        f"/cases/{ali_case_id}",
        json={"title": "Saved first", "version": first},
        headers=ali,
    ).status_code == 200

    # The second one saves what they were looking at, which is now out of date.
    response = client.patch(
        f"/cases/{ali_case_id}",
        json={"title": "Saved second", "version": second},
        headers=ali,
    )
    assert response.status_code == 409


def test_a_refused_update_changes_nothing(client, ali, ali_case_id):
    client.patch(f"/cases/{ali_case_id}", json={"title": "First", "version": 1}, headers=ali)
    client.patch(f"/cases/{ali_case_id}", json={"title": "Second", "version": 1}, headers=ali)

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()
    assert body["title"] == "First"
    assert body["version"] == 2


def test_a_caller_that_sends_no_version_still_works(client, ali, ali_case_id):
    # The check is opt-in. Leaving version out is not the same as sending a
    # stale one, so it must not be refused.
    client.patch(f"/cases/{ali_case_id}", json={"title": "One"}, headers=ali)

    response = client.patch(f"/cases/{ali_case_id}", json={"title": "Two"}, headers=ali)
    assert response.status_code == 200


def test_the_version_cannot_be_written_by_the_client(client, ali, ali_case_id):
    # version is bookkeeping, not a field anyone gets to set. Sending the
    # current one is how the check is passed - it must not also store it.
    client.patch(f"/cases/{ali_case_id}", json={"title": "A", "version": 1}, headers=ali)

    assert client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"] == 2


# --- a status change is a change, so it must move the version too ---


def test_a_status_change_moves_the_version_on(client, ali, ali_case_id):
    before = client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"]

    client.patch(f"/cases/{ali_case_id}/status", json={"status": "Active"}, headers=ali)

    after = client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"]
    assert after == before + 1


def test_a_version_from_before_a_status_change_is_refused(client, ali, ali_case_id):
    """The real situation: A moves the status while B's page sits on the old one.

    A status change used to leave the version alone, so B's stale number still
    looked current and their save went through unchallenged - even though the
    case had moved on in between.
    """
    stale = client.get(f"/cases/{ali_case_id}", headers=ali).json()["version"]

    client.patch(f"/cases/{ali_case_id}/status", json={"status": "Active"}, headers=ali)

    response = client.patch(
        f"/cases/{ali_case_id}", json={"title": "Naya title", "version": stale}, headers=ali
    )
    assert response.status_code == 409
