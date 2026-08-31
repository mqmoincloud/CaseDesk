from src.database import Base, UTCDateTime, utcnow
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class CaseStatusChange(Base):

    __tablename__ = "case_status_changes"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(ForeignKey("cases.id"), nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    changed_by_id = Column(ForeignKey("staff.id"), nullable=False)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    changed_by = relationship("Staff", foreign_keys=[changed_by_id])
