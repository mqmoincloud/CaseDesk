"""The status record - from what to what, when, and by whose hand.

The same shape as assignment history, with one difference: the first row is not
a transition. A case opens at Intake, and the opening is itself an event -
without it the timeline starts halfway through.
"""


def test_creating_a_case_records_that_it_opened_at_intake(client, ali, ali_case_id):
    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert len(body["status_changes"]) == 1
    opened = body["status_changes"][0]
    assert opened["from_status"] is None
    assert opened["to_status"] == "Intake"
    assert opened["changed_by"]["name"] == "Ali Khan"
    assert opened["created_at"]


def test_moving_the_status_records_both_ends(client, ali, ali_case_id):
    client.patch(f"/cases/{ali_case_id}/status", json={"status": "Active"}, headers=ali)

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    # Newest first, the opening row last.
    assert [(c["from_status"], c["to_status"]) for c in body["status_changes"]] == [
        ("Intake", "Active"),
        (None, "Intake"),
    ]


def test_the_whole_journey_is_kept(client, ali, ali_case_id):
    for status in ["Active", "Settled", "Closed"]:
        client.patch(
            f"/cases/{ali_case_id}/status", json={"status": status}, headers=ali
        )

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert [c["to_status"] for c in body["status_changes"]] == [
        "Closed",
        "Settled",
        "Active",
        "Intake",
    ]


def test_a_rejected_transition_records_nothing(client, ali, ali_case_id):
    # Intake straight to Settled is not allowed - 409.
    response = client.patch(
        f"/cases/{ali_case_id}/status", json={"status": "Settled"}, headers=ali
    )
    assert response.status_code == 409

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    # The opening row only, no invented transition.
    assert len(body["status_changes"]) == 1


def test_an_admin_moving_it_is_recorded_as_the_admin(client, ali, admin, ali_case_id):
    client.patch(
        f"/cases/{ali_case_id}/status", json={"status": "Active"}, headers=admin
    )

    body = client.get(f"/cases/{ali_case_id}", headers=ali).json()

    assert body["status_changes"][0]["changed_by"]["name"] == "Admin"
