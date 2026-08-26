from src.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(ForeignKey("staff.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # yeh jo niche wala relationship hai, ye sqlalchemy ka feature hai jo foreign key ke through related tables ko link karta hai. Iska matlab hai ki jab aap ek Client object create karte hain, to aap directly uske related Case objects ko access kar sakte hain.
    cases = relationship("Case", back_populates="client")
