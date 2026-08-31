from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.schemas.client import ClientOutMini
from src.schemas.staff import StaffMini
from src.schemas.note import NoteOut
from datetime import datetime


class CaseRegister(BaseModel):
    client_id: int
    assignee_id: int | None = None
    title: str = Field(min_length = 1, max_length = 200)
    case_type: str = Field(min_length = 1, max_length = 50)


class CaseAssignmentOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignee: StaffMini | None = None
    assigned_by: StaffMini
    created_at: datetime


class CaseStatusChangeOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: str | None = None
    to_status: str
    changed_by: StaffMini
    created_at: datetime


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    client: ClientOutMini
    owner: StaffMini
    assignee: StaffMini | None = None
    last_assignment: CaseAssignmentOut | None = None
    last_status_change: CaseStatusChangeOut | None = None
    case_type: str
    version: int
    created_at: datetime
    updated_at: datetime


class CaseUpdate(BaseModel):

    assignee_id: int | None = None
    title: str | None = Field(default = None, min_length = 1, max_length = 200)
    case_type: str | None = Field(default = None, min_length = 1, max_length = 50)
    version: int | None = None

    @field_validator("title", "case_type")
    @classmethod
    def cannot_be_null(cls, value):
        if value is None:
            raise ValueError("cannot be null")
        return value


class CaseDetailOut(CaseOut):

    notes: list[NoteOut] = []
    assignments: list[CaseAssignmentOut] = []
    status_changes: list[CaseStatusChangeOut] = []


class CasePageOut(BaseModel):
    items : list[CaseOut]
    total: int
    has_next: bool
    next_cursor: int | None = None


class CaseStatusUpdate(BaseModel):
 
    status: Literal["Intake", "Active", "Settled", "Closed"]
