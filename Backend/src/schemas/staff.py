from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator


class StaffRegister(BaseModel):
    name: str
    email: EmailStr 
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "staff"] = "staff"


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
    role: str
    

class StaffMini(BaseModel):
    # Just enough to put a name on a screen.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    

class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: Literal["admin", "staff"] | None = None

    # All three columns are NOT NULL, so null would reach the database and
    # come back as a 500. Leaving a field out is still fine - the default is
    # never validated.
    @field_validator("name", "email", "role")
    @classmethod
    def cannot_be_null(cls, value):
        if value is None:
            raise ValueError("cannot be null")
        return value


class ProfileOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    # Email is deliberately not here. It is the login identifier, and changing
    # it by mistake locks you out - an admin can do it if it is really needed.
    name: str = Field(min_length=1)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)
