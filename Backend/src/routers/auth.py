from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Case, Client, Staff
from src.security import hash_password, create_token, verify_password, require_admin, get_current_user
from src.schemas import TokenOut, StaffRegister, StaffLogin, StaffOut, StaffMini, StaffUpdate, ProfileOut, ProfileUpdate, PasswordChange

auth_router = APIRouter()

@auth_router.post("/auth/register", response_model = StaffOut)
def staff_registration(staff:StaffRegister, db:Session = Depends(get_db), admin = Depends(require_admin)):

    existing_staff = db.query(Staff).filter(Staff.email == staff.email.lower()).first()
    
    if existing_staff:
        raise HTTPException(status_code=409,
                             detail="Email already registered")

    new_staff = Staff(
        name = staff.name,
        email = staff.email.lower(),
        role = staff.role,
        password_hash = hash_password(staff.password)
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return new_staff


@auth_router.post("/auth/login", response_model = TokenOut)
def staff_login(staff:StaffLogin, db :Session = Depends(get_db)):

    existing_staff= db.query(Staff).filter(
        Staff.email == staff.email.lower(),
        Staff.deleted_at.is_(None),
    ).first()

    if not existing_staff or not verify_password(staff.password, existing_staff.password_hash ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({
        "sub": str(existing_staff.id),
        "ver": existing_staff.token_version,
    })

    return {
        "access_token": token,
        "token_type" : "bearer"
    }


@auth_router.get("/staff", response_model = list[StaffMini])
def all_staff(db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    return db.query(Staff).filter(Staff.deleted_at.is_(None)).order_by(Staff.name).all()


@auth_router.get("/admin/staff", response_model = list[StaffOut])
def all_staff_for_admin(db: Session = Depends(get_db), admin: Staff = Depends(require_admin)):

    return db.query(Staff).filter(Staff.deleted_at.is_(None)).order_by(Staff.name).all()


@auth_router.patch("/staff/{id}", response_model = StaffOut)
def update_staff(id: int, new_info: StaffUpdate, db: Session = Depends(get_db), admin: Staff = Depends(require_admin)):

    staff = db.query(Staff).filter(Staff.id == id, Staff.deleted_at.is_(None)).first()

    if not staff:
        raise HTTPException(status_code = 404, detail = "Staff not found")

    data = new_info.model_dump(exclude_unset = True)

    # can't change your own role
    if staff.id == admin.id and data.get("role") not in (None, staff.role):
        raise HTTPException(
            status_code = 409,
            detail = "You cannot change your own role"
        )

    if "email" in data:
        email = data["email"].lower()
        taken = db.query(Staff).filter(Staff.email == email, Staff.id != staff.id).first()

        if taken:
            raise HTTPException(status_code = 409, detail = "Email already registered")

        staff.email = email
        data.pop("email")

    # Updating Password here !!
    if data.get("password"):
        staff.password_hash = hash_password(data["password"])
        staff.token_version = staff.token_version + 1
    data.pop("password", None)

    for key, value in data.items():
        setattr(staff, key, value)

    db.commit()
    db.refresh(staff)

    return staff


@auth_router.delete("/staff/{id}", response_model = StaffOut)
def delete_staff(id: int, db: Session = Depends(get_db), admin: Staff = Depends(require_admin)):

    staff = db.query(Staff).filter(Staff.id == id, Staff.deleted_at.is_(None)).first()

    if not staff:
        raise HTTPException(status_code = 404, detail = "Staff not found")

    if staff.id == admin.id:
        raise HTTPException(
            status_code = 409,
            detail = "You cannot remove your own account"
        )

    # Cannot Delete Staff having pending cases  or clients 
    clients = db.query(Client).filter(
        Client.staff_id == staff.id, Client.deleted_at.is_(None)
    ).count()

    cases = db.query(Case).filter(
        Case.staff_id == staff.id, Case.deleted_at.is_(None)
    ).count()

    assigned = db.query(Case).filter(
        Case.assignee_id == staff.id, Case.deleted_at.is_(None)
    ).count()

    if clients or cases or assigned:
        raise HTTPException(
            status_code = 409,
            detail = "Staff still owns or is assigned clients or cases"
        )
    
    staff.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(staff)

    return staff


@auth_router.get("/me", response_model = ProfileOut)
def current_staff(current_user: Staff = Depends(get_current_user)):
  
    return current_user


@auth_router.patch("/me", response_model = ProfileOut)
def update_profile(new_info: ProfileUpdate, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_user.name = new_info.name

    db.commit()
    db.refresh(current_user)

    return current_user


@auth_router.post("/me/password", response_model = TokenOut)
def change_password(body: PasswordChange, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code = 422,
            detail = "Current password is wrong"
        )

    current_user.password_hash = hash_password(body.new_password)

    current_user.token_version = current_user.token_version + 1

    db.commit()
    db.refresh(current_user)

    # Raising token_version kills every token that was issued before this
    # point - which is the reason to change a password, but it also kills the
    # one the caller is holding right now. Handing back a fresh token signs
    # the other sessions out without signing this one out too. Without it the
    # screen says "Password changed" and the next request gets a 401.
    token = create_token({
        "sub": str(current_user.id),
        "ver": current_user.token_version,
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
