from pydantic import BaseModel, ConfigDict
from datetime import datetime
from src.schemas.staff import StaffOut

class NoteRegister(BaseModel):
    body: str

class NoteOut (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: StaffOut
    case_id: int
    body: str
    created_at: datetime


