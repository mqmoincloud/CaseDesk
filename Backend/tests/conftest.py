
import os

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.main import app

# A separate file from the app's casedesk.db, so running the suite never
# touches the data you seeded for manual testing.
TEST_DB_FILE = "pytest_casedesk.db"
TEST_DB_URL = f"sqlite:///./{TEST_DB_FILE}"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)

PASSWORD = "password123"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
   
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    alembic_config = AlembicConfig("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(alembic_config, "head")

    yield


@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        # Children first, so no foreign key is left pointing at a deleted row.
        with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())


@pytest.fixture
def client(db):

    def override_get_db():
        try:
            yield db
        finally:
            pass  # the db fixture owns closing it

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client, email):
    """Log in and return the headers that authenticate that account."""
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = response.json()["access_token"]
    # The standard Authorization header, as "Bearer <token>".
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, name, email, admin_headers):
    """Create a staff account through the API, then log in as it.

    Registration is admin-only, so this needs an admin's headers - the same
    chicken-and-egg the seed script solves by writing the first admin directly.
    """
    client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": PASSWORD},
        headers=admin_headers,
    )
    return login(client, email)


@pytest.fixture
def admin(client, db):
    """The first admin, written straight to the database.

    It cannot go through /auth/register, because that route now requires an
    admin to already exist. The seed script does the same thing.
    """
    from src.models import Staff
    from src.security import hash_password

    db.add(
        Staff(
            name="Admin",
            email="admin@example.com",
            password_hash=hash_password(PASSWORD),
            role="admin",
        )
    )
    db.commit()
    return login(client, "admin@example.com")


@pytest.fixture
def ali(client, admin):
    return register_and_login(client, "Ali Khan", "ali@example.com", admin)


@pytest.fixture
def sara(client, admin):
    """A second staff member - every isolation test needs someone to be kept out."""
    return register_and_login(client, "Sara Sheikh", "sara@example.com", admin)


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
