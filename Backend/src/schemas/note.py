from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from src.schemas.staff import StaffMini

class NoteRegister(BaseModel):

    body: str = Field(min_length = 1, max_length = 5000)

class NoteOut (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: StaffMini
    case_id: int
    body: str
    created_at: datetime
