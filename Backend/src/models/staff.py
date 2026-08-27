from src.database import Base, UTCDateTime, utcnow
from sqlalchemy import Column, Integer, String

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key = True, index= True)
    name = Column(String, nullable = False)
    email = Column(String, unique = True, nullable = False)
    password_hash = Column(String, nullable = False)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    updated_at = Column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)