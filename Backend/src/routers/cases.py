from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from src.database import get_db
from src.models import Staff, Client, Case
from src.schemas import CaseRegister, CaseOut, CaseUpdate, CaseDetailOut,CasePageOut, CaseStatusUpdate
from src.security import get_current_user

cases_router = APIRouter()


ALLOWED_TRANSITIONS = {                
    "Intake":  ["Active"],
    "Active":  ["Settled"],
    "Settled": ["Closed"],
    "Closed":  [],
}


@cases_router.post("/cases/registration", response_model = CaseOut)
def case_registration (case_info: CaseRegister, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    client = db.query(Client).filter(Client.id == case_info.client_id, Client.staff_id == current_user.id, Client.deleted_at.is_(None)).first()

    if not client:
        raise HTTPException(
            status_code = 404,
            detail = "Client not found"
            )

    # Here verify assignee if it exists or not ..'.
    if case_info.assignee_id:
        assignee = db.query(Staff).filter(
            Staff.id == case_info.assignee_id
        ).first()

        if not assignee :
            raise HTTPException(status_code = 404, detail = "Assignee not found")

    new_case = Case(
            client_id = case_info.client_id,
            staff_id = current_user.id,
            assignee_id= case_info.assignee_id,
            title= case_info.title,
            case_type= case_info.case_type
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return new_case


@cases_router.get("/cases/{id}", response_model = CaseDetailOut)
def case_details (id:int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_case = db.query(Case).filter(Case.id == id, Case.staff_id == current_user.id, Case.deleted_at.is_(None)).first()

    if not current_case:
        raise HTTPException(
                    status_code = 404,
                    detail = "Case not found"
                    )

    return current_case


@cases_router.get("/cases", response_model = CasePageOut)
def all_cases (status:str | None = None, page:int = 1, limit: int =10,assignee:int | None = None, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    all_cases = db.query(Case).options(
        selectinload(Case.client),
        selectinload(Case.assignee)
    ).filter(Case.staff_id == current_user.id, Case.deleted_at.is_(None))

    if status:
        all_cases = all_cases.filter(Case.status == status)

    if assignee:
        all_cases = all_cases.filter(Case.assignee_id == assignee)

    total = all_cases.count()

    items = all_cases.order_by(Case.id).offset((page - 1) * limit).limit(limit).all()
    has_next = (page * limit) < total
    return {"items": items, "total": total, "has_next": has_next}


@cases_router.patch("/cases/{id}", response_model = CaseOut)
def update_case (id: int, new_info: CaseUpdate, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_case = db.query(Case).filter( Case.id == id, Case.staff_id == current_user.id, Case.deleted_at.is_(None)).first()

    if not current_case: 
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
            )

    data = new_info.model_dump(exclude_unset = True)

    if new_info.assignee_id:
        assignee = db.query(Staff).filter(Staff.id == new_info.assignee_id).first()

        if not assignee:
            raise HTTPException(
            status_code = 404,
            detail = "Assignee not found"
            )

    for key, value in data.items():
        setattr(current_case, key, value)

    db.commit()
    db.refresh(current_case)

    return current_case


@cases_router.patch("/cases/{id}/status", response_model = CaseOut)
def status_update(id: int, new_info: CaseStatusUpdate, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_case = db.query(Case).filter(Case.id == id, Case.staff_id == current_user.id, Case.deleted_at.is_(None)).first()

    if not current_case:
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
            )

    if new_info.status not in ALLOWED_TRANSITIONS[current_case.status] :
        raise HTTPException(
            status_code = 409,
            detail = f"Cannot change status from {current_case.status} to {new_info.status}"
            )

    current_case.status = new_info.status

    db.commit()
    db.refresh(current_case)

    return current_case










