from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.types import TypeDecorator
from src.config import config

engine = create_engine(
    config.db_url, 
    connect_args={"check_same_thread": False}
    )

localSession = sessionmaker(bind = engine)

Base = declarative_base()


class UTCDateTime(TypeDecorator):
    """A datetime column that is always UTC and always timezone-aware.

    SQLite has no timezone-aware type - it drops the offset on the way in and
    hands back a naive datetime on the way out. This puts the timezone back at
    the edges: everything is converted to UTC before it is written, and comes
    back tagged as UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Going into the database."""
        if value is None:
            return None
        if value.tzinfo is None:
            # Anything naive reaching this point is already meant to be UTC.
            value = value.replace(tzinfo=timezone.utc)
        # Stored without the offset, because that is all SQLite can hold.
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """Coming back out of the database."""
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


def utcnow():
    """Default for created_at / updated_at.

    Python-side rather than server_default=func.now(): SQLite's CURRENT_TIMESTAMP
    never passes through UTCDateTime above, so those values would skip the
    conversion entirely.
    """
    return datetime.now(timezone.utc)

def get_db():
    db = localSession()
    try:
        yield db
    finally:
        db.close()