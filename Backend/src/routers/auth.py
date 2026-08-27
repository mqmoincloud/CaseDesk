from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Staff
from src.security import hash_password, create_token, verify_password
from src.schemas import TokenOut, StaffRegister, StaffLogin, StaffOut
from src.security import get_current_user

auth_router = APIRouter()

@auth_router.post("/auth/register", response_model = StaffOut)
def staff_registration(staff:StaffRegister, db:Session = Depends(get_db)):

    existing_staff = db.query(Staff).filter(Staff.email == staff.email.lower()).first()
    
    if existing_staff:
        raise HTTPException(status_code=409,
                             detail="Email already registered")

    new_staff = Staff(
        name = staff.name,
        email = staff.email.lower(),
        password_hash = hash_password(staff.password)
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return new_staff


@auth_router.post("/auth/login", response_model = TokenOut)
def staff_login(staff:StaffLogin, db :Session = Depends(get_db)):
    existing_staff= db.query(Staff).filter(Staff.email == staff.email.lower()).first()

    if not existing_staff or not verify_password(staff.password, existing_staff.password_hash ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": str(existing_staff.id)})

    return {
        "access_token": token,
        "token_type" : "bearer"
    }


@auth_router.get("/staff", response_model = list[StaffOut])
def all_staff(db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    # Not filtered by owner. A case can be assigned to any colleague, so the
    # assignee dropdown has to show everyone. Only id, name and email go out -
    # StaffOut has no password_hash field at all.
    return db.query(Staff).order_by(Staff.name).all()
