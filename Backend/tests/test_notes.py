"""Epic 4 - notes (US-13, US-14)."""


def test_add_a_note(client, ali, ali_case_id):
    response = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Client called"}, headers=ali
    )
    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Client called"
    assert body["author"]["name"] == "Ali Khan"
    assert body["created_at"] is not None


def test_author_cannot_be_spoofed_through_the_body(client, ali, sara, ali_case_id, db):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    # US-13: author comes from the token, so a staff_id in the body is ignored.
    response = client.post(
        f"/cases/{ali_case_id}/notes",
        json={"body": "Pretending to be Sara", "staff_id": sara_id},
        headers=ali,
    )
    assert response.json()["author"]["name"] == "Ali Khan"


def test_note_on_another_staffs_case_returns_404(client, ali, sara, ali_case_id):
    response = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Intruding"}, headers=sara
    )
    assert response.status_code == 404


def test_note_on_unknown_case_returns_404(client, ali):
    response = client.post("/cases/99999/notes", json={"body": "x"}, headers=ali)
    assert response.status_code == 404


def test_notes_come_back_newest_first(client, ali, ali_case_id):
    for text in ["oldest", "middle", "newest"]:
        client.post(f"/cases/{ali_case_id}/notes", json={"body": text}, headers=ali)

    notes = client.get(f"/cases/{ali_case_id}", headers=ali).json()["notes"]
    # US-13: newest first on the case detail page. Ids rise with insertion order,
    # so a descending id sequence is the same claim without relying on the clock,
    # which can put several inserts in the same second.
    ids = [note["id"] for note in notes]
    assert ids == sorted(ids, reverse=True)
    assert notes[0]["body"] == "newest"


def test_delete_a_note_is_soft(client, ali, ali_case_id, db):
    from src.models import Note

    note_id = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Mistake"}, headers=ali
    ).json()["id"]

    assert client.delete(f"/notes/{note_id}", headers=ali).status_code == 200

    row = db.query(Note).filter(Note.id == note_id).first()
    assert row is not None
    assert row.deleted_at is not None


def test_deleted_note_disappears_from_the_case(client, ali, ali_case_id):
    note_id = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Mistake"}, headers=ali
    ).json()["id"]
    client.post(f"/cases/{ali_case_id}/notes", json={"body": "Keeper"}, headers=ali)

    client.delete(f"/notes/{note_id}", headers=ali)

    notes = client.get(f"/cases/{ali_case_id}", headers=ali).json()["notes"]
    assert [note["body"] for note in notes] == ["Keeper"]


def test_deleting_the_same_note_twice_returns_404(client, ali, ali_case_id):
    note_id = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "x"}, headers=ali
    ).json()["id"]

    client.delete(f"/notes/{note_id}", headers=ali)
    assert client.delete(f"/notes/{note_id}", headers=ali).status_code == 404


def test_only_notes_on_my_own_cases_can_be_deleted(client, ali, sara, ali_case_id):
    note_id = client.post(
        f"/cases/{ali_case_id}/notes", json={"body": "Ali's note"}, headers=ali
    ).json()["id"]

    # US-14: ownership is the case's, so Sara must not reach it.
    assert client.delete(f"/notes/{note_id}", headers=sara).status_code == 404
