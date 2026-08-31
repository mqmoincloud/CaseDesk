from src.database import Base, UTCDateTime, utcnow
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key = True, index = True)
    client_id = Column(ForeignKey("clients.id"), nullable = False, index = True)
    staff_id = Column(ForeignKey("staff.id"), nullable = False, index = True)
    assignee_id = Column(ForeignKey("staff.id"), nullable = True, index = True)
    title = Column(String, nullable = False)
    case_type = Column(String, nullable = False)
    status = Column(String , default = "Intake", nullable = False)
    created_at = Column(UTCDateTime, default=utcnow, nullable=False)
    updated_at = Column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(UTCDateTime, nullable=True)
    version = Column(Integer, nullable = False, default = 1)
    client = relationship("Client", back_populates="cases")
    assignee = relationship("Staff", foreign_keys=[assignee_id])
    owner = relationship("Staff", foreign_keys=[staff_id])
    
    notes = relationship(
        "Note",
        primaryjoin="and_(Case.id == Note.case_id, Note.deleted_at.is_(None))",
        order_by="Note.created_at.desc(), Note.id.desc()",
        viewonly=True,
    )

    assignments = relationship(
        "CaseAssignment",
        order_by="CaseAssignment.created_at.desc(), CaseAssignment.id.desc()",
        viewonly=True,
    )

    status_changes = relationship(
        "CaseStatusChange",
        order_by="CaseStatusChange.created_at.desc(), CaseStatusChange.id.desc()",
        viewonly=True,
    )

    @property
    def last_assignment(self):
        """The list needs who assigned it now, not the whole history."""
        return self.assignments[0] if self.assignments else None

    @property
    def last_status_change(self):
        return self.status_changes[0] if self.status_changes else None
