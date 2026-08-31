from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
from src.config import config
from passlib.context import CryptContext
from sqlalchemy import or_, true
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
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.token_minutes)
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)

    return token


bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):

    if credentials is None:
        raise HTTPException(
            status_code = 401,
            detail = "Not authenticated"
        )

    try:
        # .credentials is the part after "Bearer ".
        payload = jwt.decode(credentials.credentials, config.secret_key, algorithms=[config.algorithm])
        return payload
    
    except JWTError:
        raise HTTPException(
            status_code = 401,
            detail = "Invalid or expired token"
        )


def get_current_user(user_data: dict = Depends(verify_token), db : Session = Depends(get_db)):

    current_staff = db.query(Staff).filter(
        Staff.id == user_data.get("sub"),
        Staff.deleted_at.is_(None),
    ).first()

    if not current_staff :
        raise HTTPException(
            status_code = 401,
            detail = "User is Not verified"
        )

    if user_data.get("ver") != current_staff.token_version:
        raise HTTPException(
            status_code = 401,
            detail = "Invalid or expired token"
        )

    return current_staff


def case_visible_to(user):
    if user.role == "admin":
        return true()
    return or_(Case.staff_id == user.id, Case.assignee_id == user.id)


def owned_by(user, model):
    if user.role == "admin":
        return true()

    return model.staff_id == user.id


def require_admin(current_user:Staff = Depends(get_current_user)):
    if current_user.role != "admin":
            raise HTTPException(
                status_code = 403,
                detail = "Admins Only"
            )
    return current_user
