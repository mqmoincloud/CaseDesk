"""NF-06 - timestamps are UTC and timezone-aware.

SQLite cannot store an offset, so the UTCDateTime type in database.py puts the
timezone back at the edges. These tests are what stops that quietly regressing:
swap UTCDateTime back for a plain DateTime and every one of them fails.
"""

from datetime import datetime, timedelta, timezone

from src.models import Case, Client, Note, Staff


def test_created_at_comes_back_timezone_aware(client, ali, ali_client_id, db):
    row = db.query(Client).filter(Client.id == ali_client_id).first()

    assert row.created_at.tzinfo is not None
    assert row.created_at.utcoffset() == timedelta(0)


def test_every_table_stores_aware_timestamps(client, ali, ali_case_id, db):
    client.post(f"/cases/{ali_case_id}/notes", json={"body": "note"}, headers=ali)

    for model in (Staff, Client, Case, Note):
        row = db.query(model).first()
        assert row.created_at.tzinfo is not None, f"{model.__name__}.created_at is naive"


def test_the_api_sends_the_offset(client, ali, ali_client_id):
    body = client.get(f"/clients/{ali_client_id}", headers=ali).json()

    # A bare "2026-08-27T05:20:50" would leave the caller guessing which zone
    # it is in. fromisoformat only produces an aware datetime if the offset is
    # actually in the string.
    parsed = datetime.fromisoformat(body["created_at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_updated_at_stays_aware_after_an_edit(client, ali, ali_client_id):
    client.patch(f"/clients/{ali_client_id}", json={"phone": "999"}, headers=ali)

    body = client.get(f"/clients/{ali_client_id}", headers=ali).json()
    assert datetime.fromisoformat(body["updated_at"]).tzinfo is not None


def test_soft_delete_timestamp_is_aware(client, ali, ali_client_id, db):
    client.delete(f"/clients/{ali_client_id}", headers=ali)

    row = db.query(Client).filter(Client.id == ali_client_id).first()
    assert row.deleted_at is not None
    assert row.deleted_at.tzinfo is not None


def test_a_naive_value_written_directly_is_read_back_as_utc(client, ali, db):
    """Old rows, or anything written without a timezone, are treated as UTC."""
    naive = datetime(2026, 1, 1, 12, 0, 0)

    staff = db.query(Staff).first()
    row = Client(staff_id=staff.id, name="Naive", created_at=naive, updated_at=naive)
    db.add(row)
    db.commit()
    db.expire(row)

    assert row.created_at.tzinfo is timezone.utc
    assert row.created_at.hour == 12


def test_an_offset_value_is_converted_to_utc_before_storing(client, ali, db):
    """A time sent in another zone is normalised, not stored as-is."""
    # 17:30 in +05:30 is 12:00 UTC.
    ist = datetime(2026, 1, 1, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    staff = db.query(Staff).first()
    row = Client(staff_id=staff.id, name="IST", created_at=ist, updated_at=ist)
    db.add(row)
    db.commit()
    db.expire(row)

    assert row.created_at.hour == 12
    assert row.created_at.utcoffset() == timedelta(0)
