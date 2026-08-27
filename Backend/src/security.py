from jose import jwt 
from fastapi import Header, HTTPException, Depends
from datetime import datetime, timedelta, timezone
from src.config import config
from passlib.context import CryptContext
from sqlalchemy import or_
from src.models import Case, Staff
from sqlalchemy.orm import Session
from src.database import get_db


pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain_password:str, hashed_password:str):
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)

    return token


def verify_token(token:str = Header(None)):
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        return payload
    except:
        raise HTTPException(
            status_code = 401,
            detail = "Invalid or expired token"
        )


def get_current_user(token: str= Header(None), db : Session = Depends(get_db)):
    user_data = verify_token(token)
    current_staff = db.query(Staff).filter(Staff.id == user_data.get("sub")).first()

    if not current_staff :
        raise HTTPException(
            status_code = 401,
            detail = "User is Not verified"
        )

    return current_staff


def case_visible_to(user):
    return or_(Case.staff_id == user.id, Case.assignee_id == user.id)
