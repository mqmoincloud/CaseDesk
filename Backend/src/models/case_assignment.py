from src.database import Base, UTCDateTime, utcnow
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship


class CaseAssignment(Base):

    __tablename__ = "case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(ForeignKey("cases.id"), nullable=False, index=True)
    assignee_id = Column(ForeignKey("staff.id"), nullable=True)
    assigned_by_id = Column(ForeignKey("staff.id"), nullable=False)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    assignee = relationship("Staff", foreign_keys=[assignee_id])
    assigned_by = relationship("Staff", foreign_keys=[assigned_by_id])
