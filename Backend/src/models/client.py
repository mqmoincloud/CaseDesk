from src.database import Base, UTCDateTime, utcnow
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(ForeignKey("staff.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    updated_at = Column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(UTCDateTime, nullable=True)
    cases = relationship("Case", back_populates="client")
