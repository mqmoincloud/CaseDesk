from pydantic import BaseModel, ConfigDict
from src.schemas.client import ClientOutMini
from src.schemas.staff import StaffOut
from src.schemas.note import NoteOut
from datetime import datetime

class CaseRegister(BaseModel):
    client_id: int
    assignee_id: int | None = None
    title: str
    # status: str = Field(default="Intake")
    case_type: str 
    # version: int

class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    client: ClientOutMini
    # staff: StaffOut
    assignee: StaffOut | None = None
    case_type: str
    version: int
    created_at: datetime
    updated_at: datetime

class CaseUpdate(BaseModel):
    assignee_id: int | None = None
    title: str | None = None
    # status: str | None = None
    case_type: str | None = None
    version: int | None = None

class CaseDetailOut(CaseOut):
    notes: list[NoteOut] = []

class CasePageOut(BaseModel):
    items : list[CaseOut]
    total: int
    has_next: bool
    next_cursor: int | None = None

class CaseStatusUpdate(BaseModel):
    status: str
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    