from pydantic import BaseModel, ConfigDict, Field, EmailStr

class StaffRegister(BaseModel):
    name: str
    email: EmailStr 
    password: str = Field(min_length=8)

class StaffLogin(BaseModel):
    email: EmailStr 
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str

class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr 

class StaffUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)