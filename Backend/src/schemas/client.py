from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from src.schemas.staff import StaffMini

PHONE = r"^\+?[\d\s-]{7,20}$"

class ClientRegister(BaseModel):
    name: str = Field(min_length =1)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=PHONE)
    address: str | None = None
    staff_id: int | None = None

class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    owner: StaffMini
    created_at: datetime
    updated_at: datetime

class ClientOutMini(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id : int
    name : str

class ClientUpdate(BaseModel):
   
    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=PHONE)
    address: str | None = None

    @field_validator("name")
    @classmethod
    def name_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("name cannot be null")
        return value

class ClientPage(BaseModel):
    items: list[ClientOut]
    total : int 
    has_next: bool
    next_cursor: int | None = None

