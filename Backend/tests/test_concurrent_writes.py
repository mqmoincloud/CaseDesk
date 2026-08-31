"""US-21 - what happens when two people really do save at the same moment.

`test_concurrent_edits.py` proves a stale version gets a 409. That is necessary
but it is not a race: TestClient finishes one request before starting the next,
so the second one always reads the fresh version.

The bug this file exists for needed both writers running at once. The old code
read the row, compared the version in Python, then wrote - with no lock across
the three steps. Four threads all got 200 and the version went from 1 to 2:
three people's work vanished and all three were told it had saved.

So this file runs a real server. Two details carry the test, and without either
one it goes green while proving nothing:

  1. A session per request. The `client` fixture in `conftest.py` shares one
     session for the whole test, and two requests inside one session see each
     other, so no race can form.

  2. `threading.Barrier`. Simply starting threads is not enough - the first has
     usually finished before the last begins. The barrier holds all four and
     releases them together.
"""

import socket
import threading

import pytest
import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import get_db
from src.main import app
from src.models import Staff
from src.security import hash_password

PASSWORD = "password123"
WRITERS = 4


def free_port():
    """Ask the OS for a free port rather than hardcoding one."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """A real uvicorn server, on its own database file."""
    db_file = tmp_path_factory.mktemp("race") / "race.db"
    url = f"sqlite:///{db_file}"

    alembic_config = AlembicConfig("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_config, "head")

    # timeout: SQLite refuses a second concurrent writer immediately. This asks
    # it to wait instead, so the test fails on the race rather than on
    # "database is locked".
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Session = sessionmaker(bind=engine)

    def fresh_session_per_request():
        # A session per request - exactly what the real app does.
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = fresh_session_per_request

    # The first admin goes straight into the database: register is admin-only.
    setup = Session()
    setup.add(
        Staff(
            name="Admin",
            email="admin@example.com",
            password_hash=hash_password(PASSWORD),
            role="admin",
        )
    )
    setup.commit()
    setup.close()

    port = free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started:
        if not thread.is_alive():
            pytest.fail("server chala hi nahi")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def api(live_server):
    """httpx2 is the same client TestClient uses underneath."""
    import httpx2

    with httpx2.Client(base_url=live_server, timeout=30) as client:
        token = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": PASSWORD},
        ).json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture
def a_case(api):
    """A fresh case per test, so no two tests touch the same row."""
    client_id = api.post("/clients/registration", json={"name": "Racer"}).json()["id"]
    return api.post(
        "/cases/registration",
        json={"client_id": client_id, "title": "Before", "case_type": "Civil"},
    ).json()


def run_together(work):
    """Run `work` in WRITERS threads released together, and return the results."""
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(WRITERS)

    def worker(index):
        barrier.wait()
        outcome = work(index)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(WRITERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(results) == WRITERS, "a thread never finished"
    return results


def test_only_one_of_several_simultaneous_saves_gets_through(api, a_case):
    """Four people looking at the same version press Save together.

    One save must survive and three must be refused outright. All four used to
    get a 200, and three people's work disappeared without anyone being told.
    """
    case_id, version = a_case["id"], a_case["version"]

    codes = run_together(
        lambda i: api.patch(
            f"/cases/{case_id}",
            json={"title": f"Saved by {i}", "version": version},
        ).status_code
    )

    assert codes.count(200) == 1, f"{codes.count(200)} writes ek saath nikal gaye: {codes}"
    assert codes.count(409) == WRITERS - 1, codes


def test_the_version_moves_exactly_once(api, a_case):
    """One write got through, so the version must move exactly once.

    This is the other half of the test above rather than a catch on its own -
    the old broken code also went from 1 to 2, because all four read the same
    number and wrote the same one back. What it guards is that
    `Case.version + 1` stays in SQL: move it back into Python and this fails
    alongside the test above.
    """
    case_id, version = a_case["id"], a_case["version"]

    run_together(
        lambda i: api.patch(
            f"/cases/{case_id}",
            json={"title": f"Saved by {i}", "version": version},
        ).status_code
    )

    assert api.get(f"/cases/{case_id}").json()["version"] == version + 1


def test_the_case_keeps_the_one_title_that_won(api, a_case):
    """The surviving title belongs to one of the writers that got a 200.

    This is the damage a user would actually see: the last request's title used
    to win, even though three others had been told they succeeded.
    """
    case_id, version = a_case["id"], a_case["version"]

    codes = run_together(
        lambda i: (
            i,
            api.patch(
                f"/cases/{case_id}",
                json={"title": f"Saved by {i}", "version": version},
            ).status_code,
        )
    )

    winners = [f"Saved by {i}" for i, code in codes if code == 200]
    assert api.get(f"/cases/{case_id}").json()["title"] == winners[0]


def test_only_one_of_several_simultaneous_status_moves_gets_through(api, a_case):
    """The status route guards on the status, not on the version.

    No version is sent here, so the protection is `WHERE status = 'Intake'`.
    Without it all four would move Intake -> Active and the timeline would carry
    four rows for one change.
    """
    case_id = a_case["id"]

    codes = run_together(
        lambda i: api.patch(
            f"/cases/{case_id}/status", json={"status": "Active"}
        ).status_code
    )

    assert codes.count(200) == 1, codes

    # And two rows in the timeline: opened, then moved to Active once.
    history = api.get(f"/cases/{case_id}").json()["status_changes"]
    assert [(row["from_status"], row["to_status"]) for row in history] == [
        ("Intake", "Active"),
        (None, "Intake"),
    ]
