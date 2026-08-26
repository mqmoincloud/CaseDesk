from pydantic import BaseModel, ConfigDict
from datetime import datetime
from src.schemas.staff import StaffOut

class NoteRegister(BaseModel):
    # title: str
    # description: str
    # case_id: int
    # staff_id: int
    body: str

class NoteOut (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # title: str
    # description: str
    author: StaffOut
    case_id: int
    # staff_id: int
    body: str
    created_at: datetime


