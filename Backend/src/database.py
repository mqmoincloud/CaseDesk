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

    return datetime.now(timezone.utc)

def like_term(search):

    cleaned = search.lower()
    cleaned = cleaned.replace("\\", "\\\\")
    cleaned = cleaned.replace("%", "\\%")
    cleaned = cleaned.replace("_", "\\_")
    return f"%{cleaned}%"


def get_db():
    db = localSession()
    try:
        yield db
    finally:
        db.close()