from src.database import Base
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey ,func
from sqlalchemy.orm import relationship


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key = True, index = True)
    client_id = Column(ForeignKey("clients.id"), nullable = False)
    staff_id = Column(ForeignKey("staff.id"), nullable = False)
    assignee_id = Column(ForeignKey("staff.id"), nullable = True)
    title = Column(String, nullable = False)
    case_type = Column(String, nullable = False)
    status = Column(String , default = "Intake", nullable = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable = False, default = 1)

    # yeh jo niche wala relationship hai, ye sqlalchemy ka feature hai jo foreign key ke through related tables ko link karta hai. Iska matlab hai ki jab aap ek Case object create karte hain, to aap directly uske related Client aur Staff objects ko access kar sakte hain.
    client = relationship("Client", back_populates="cases")
    assignee = relationship("Staff", foreign_keys=[assignee_id])
    notes = relationship("Note", primaryjoin="and_(Case.id == Note.case_id, Note.deleted_at.is_(None))", order_by= "Note.created_at.desc(), Note.id.desc()", viewonly=True,
)
