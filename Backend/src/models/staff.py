from src.database import Base
from sqlalchemy import Column, Integer, String, DateTime, func

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key = True, index= True)
    name = Column(String, nullable = False)
    email = Column(String, unique = True, nullable = False)
    password_hash = Column(String, nullable = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)