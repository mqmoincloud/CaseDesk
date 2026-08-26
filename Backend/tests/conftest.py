"""Shared test setup (NF-03: tests run against a real database).

The database here is a real SQLite file, just a different one from the app's.
Nothing is mocked - every test goes through FastAPI, through SQLAlchemy, and
hits actual tables, so a broken query fails a test instead of slipping past a
fake session.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.main import app

# A separate file from the app's test.db, so running the suite never touches
# the data you seeded for manual testing.
TEST_DB_URL = "sqlite:///./pytest_casedesk.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)

PASSWORD = "password123"


@pytest.fixture
def db():
    """A clean set of tables for one test, dropped again afterwards.

    Dropping between tests is what keeps them independent: a count assertion
    in one test can't be thrown off by rows another test happened to leave
    behind, and the order the tests run in stops mattering.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """A TestClient whose requests hit the test database.

    Every route asks for its session with Depends(get_db). dependency_overrides
    swaps in a replacement for that one dependency, so the whole app moves onto
    the test database without a single route knowing about it.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass  # the db fixture owns closing it

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client, name, email):
    """Create a staff account and return the headers that authenticate it."""
    client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": PASSWORD},
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    token = response.json()["access_token"]
    # The app reads a header literally named "token", not Authorization.
    return {"token": token}


@pytest.fixture
def ali(client):
    return register_and_login(client, "Ali Khan", "ali@example.com")


@pytest.fixture
def sara(client):
    """A second staff member - every isolation test needs someone to be kept out."""
    return register_and_login(client, "Sara Sheikh", "sara@example.com")


@pytest.fixture
def ali_client_id(client, ali):
    """One client owned by Ali, for tests that need something to hang a case off."""
    response = client.post(
        "/clients/registration",
        json={
            "name": "Ramesh Kumar",
            "email": "ramesh@example.com",
            "phone": "9876543210",
            "address": "1 Main Road, Delhi",
        },
        headers=ali,
    )
    return response.json()["id"]


@pytest.fixture
def ali_case_id(client, ali, ali_client_id):
    """One case owned by Ali, starting at Intake."""
    response = client.post(
        "/cases/registration",
        json={
            "client_id": ali_client_id,
            "title": "Property dispute",
            "case_type": "Civil",
        },
        headers=ali,
    )
    return response.json()["id"]
