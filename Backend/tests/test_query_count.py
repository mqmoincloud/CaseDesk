"""US-20 - list endpoints must not issue one query per row.

The brief says to verify by turning on query logging and counting the
statements actually issued for a 50-row page. The listener below is that
query log: SQLAlchemy fires before_cursor_execute once per statement that
reaches the database, so the length of the list is the honest count.
"""

import pytest
from sqlalchemy import event

from tests.conftest import engine

PAGE_SIZE = 50


@pytest.fixture
def count_queries():
    """Record every statement sent to the database while the block runs."""
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.fixture
def fifty_cases(client, ali, sara, db):
    from src.models import Staff

    sara_id = db.query(Staff).filter(Staff.email == "sara@example.com").first().id

    for i in range(PAGE_SIZE):
        # A fresh client each time, so the list cannot get away with loading
        # one client and reusing it for every row.
        client_id = client.post(
            "/clients/registration", json={"name": f"Client {i:03d}"}, headers=ali
        ).json()["id"]
        client.post(
            "/cases/registration",
            json={
                "client_id": client_id,
                "title": f"Case {i:03d}",
                "case_type": "Civil",
                # Alternating assignee, so that relationship has to be loaded too.
                "assignee_id": sara_id if i % 2 else None,
            },
            headers=ali,
        )


def test_a_fifty_row_page_stays_at_a_handful_of_queries(client, ali, fifty_cases, count_queries):
    count_queries.clear()

    body = client.get(f"/cases?page=1&limit={PAGE_SIZE}", headers=ali).json()

    # Touch every name, which is what the real response does when it serialises.
    names = [(row["client"]["name"], row["assignee"]) for row in body["items"]]

    assert len(names) == PAGE_SIZE
    # Expected: one count, one for the cases, one for the clients, one for the
    # assignees - plus the token lookup that authenticates the request.
    # A lazy-loading version would sit near 100 instead.
    assert len(count_queries) <= 10, (
        f"{len(count_queries)} statements for {PAGE_SIZE} rows:\n"
        + "\n".join(s.split("\n")[0][:80] for s in count_queries)
    )


def test_the_query_count_does_not_grow_with_the_page_size(client, ali, fifty_cases, count_queries):
    """The real N+1 check: ten rows and fifty rows must cost the same."""
    count_queries.clear()
    client.get("/cases?page=1&limit=10", headers=ali).json()
    small = len(count_queries)

    count_queries.clear()
    client.get(f"/cases?page=1&limit={PAGE_SIZE}", headers=ali).json()
    large = len(count_queries)

    assert small == large, f"10 rows cost {small} queries, {PAGE_SIZE} rows cost {large}"
