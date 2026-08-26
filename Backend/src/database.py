from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import config

# DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    config.db_url, 
    connect_args={"check_same_thread": False}
    )

localSession = sessionmaker(bind = engine)

Base = declarative_base()

# Base.metadata.create_all(bind=engine)

def get_db():
    db = localSession()
    try:
        yield db
    finally:
        db.close()