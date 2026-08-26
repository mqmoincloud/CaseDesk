from pydantic import BaseModel, ConfigDict, EmailStr 
from datetime import datetime

class ClientRegister(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None

class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime

class ClientOutMini(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id : int
    name : str

class ClientUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None

class ClientPage(BaseModel):
    items: list[ClientOut]
    total : int 
    has_next : bool

