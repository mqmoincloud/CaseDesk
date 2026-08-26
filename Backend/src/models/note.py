from src.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key = True, index = True)
    case_id = Column(ForeignKey("cases.id"), nullable = False)
    staff_id = Column(ForeignKey("staff.id"), nullable = False)
    body = Column(String, nullable = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # yeh jo niche wala relationship hai, ye sqlalchemy ka feature hai jo foreign key ke through related tables ko link karta hai. Iska matlab hai ki jab aap ek Note object create karte hain, to aap directly uske related Case aur Staff objects ko access kar sakte hain.
    author = relationship("Staff")
