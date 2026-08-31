from src.database import Base, UTCDateTime, utcnow
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key = True, index = True)
    case_id = Column(ForeignKey("cases.id"), nullable = False, index = True)
    staff_id = Column(ForeignKey("staff.id"), nullable = False, index = True)
    body = Column(String, nullable = False)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    deleted_at = Column(UTCDateTime, nullable=True)
    author = relationship("Staff")
