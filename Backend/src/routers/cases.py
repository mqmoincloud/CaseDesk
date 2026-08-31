from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload
from src.database import get_db, like_term
from src.models import Staff, Client, Case, CaseAssignment, CaseStatusChange
from src.schemas import CaseRegister, CaseOut, CaseUpdate, CaseDetailOut,CasePageOut, CaseStatusUpdate
from src.security import case_visible_to, get_current_user, owned_by

cases_router = APIRouter()


ALLOWED_TRANSITIONS = {                
    "Intake":  ["Active"],
    "Active":  ["Settled"],
    "Settled": ["Closed"],
    "Closed":  [],
}


@cases_router.post("/cases/registration", response_model = CaseOut)
def case_registration (case_info: CaseRegister, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    client = db.query(Client).filter(Client.id == case_info.client_id, owned_by(current_user, Client), Client.deleted_at.is_(None)).first()

    if not client:
        raise HTTPException(
            status_code = 404,
            detail = "Client not found"
            )

    # The assignee has to exist and still be active. Same check as the one in
    # update_case - a removed account is not in /staff, so it must not be
    # reachable here either.
    if case_info.assignee_id:
        assignee = db.query(Staff).filter(
            Staff.id == case_info.assignee_id,
            Staff.deleted_at.is_(None),
        ).first()

        if not assignee :
            raise HTTPException(status_code = 404, detail = "Assignee not found")

    new_case = Case(
            client_id = case_info.client_id,
            staff_id = client.staff_id,
            assignee_id= case_info.assignee_id,
            title= case_info.title,
            case_type= case_info.case_type
    )

    db.add(new_case)
    # flush gives us the id without committing, so the case and its history
    # row land in one transaction.
    db.flush()

    # Not a transition - the case opened at Intake.
    db.add(CaseStatusChange(
        case_id=new_case.id,
        from_status=None,
        to_status=new_case.status,
        changed_by_id=current_user.id,
    ))

    if new_case.assignee_id:
        db.add(CaseAssignment(
            case_id=new_case.id,
            assignee_id=new_case.assignee_id,
            assigned_by_id=current_user.id,
        ))

    db.commit()
    db.refresh(new_case)

    return new_case


@cases_router.get("/cases/{id}", response_model = CaseDetailOut)
def case_details (id:int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    # Visible to the owner and to the assignee.
    current_case = db.query(Case).options(
        selectinload(Case.assignments).selectinload(CaseAssignment.assigned_by),
        selectinload(Case.assignments).selectinload(CaseAssignment.assignee),
        selectinload(Case.status_changes).selectinload(CaseStatusChange.changed_by),
    ).filter(Case.id == id, case_visible_to(current_user), Case.deleted_at.is_(None)).first()

    if not current_case:
        raise HTTPException(
                    status_code = 404,
                    detail = "Case not found"
                    )

    return current_case


@cases_router.get("/cases", response_model = CasePageOut)
def all_cases(

    status: Literal["Intake", "Active", "Settled", "Closed"] | None = None,
    before: int | None = Query(None, ge=1),
    limit: int = Query(10, ge=1, le=100),
    assignee: int | None = Query(None, ge=1),
    owner: int | None = Query(None, ge=1),
    client_id: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):

    all_cases = db.query(Case).options(
        selectinload(Case.client),
        selectinload(Case.assignee),
        selectinload(Case.owner),
        selectinload(Case.assignments).selectinload(CaseAssignment.assigned_by),
        selectinload(Case.status_changes).selectinload(CaseStatusChange.changed_by)
    ).filter(case_visible_to(current_user), Case.deleted_at.is_(None))

    if status is not None:
        all_cases = all_cases.filter(Case.status == status)

    if assignee is not None:
        all_cases = all_cases.filter(Case.assignee_id == assignee)

    # Who the case belongs to. An assignee sees other people's cases in this
    # list, so "show me only mine" needs its own filter.
    if owner is not None:
        all_cases = all_cases.filter(Case.staff_id == owner)

    if client_id is not None:
        all_cases = all_cases.filter(Case.client_id == client_id)

    if search is not None and search != "":
        term = like_term(search)

        all_cases = all_cases.join(Case.client).filter(or_(
            func.lower(Case.title).like(term, escape="\\"),
            func.lower(Case.case_type).like(term, escape="\\"),
            func.lower(Client.name).like(term, escape="\\"),
        ))

    total = all_cases.count()

    # Same cursor paging as /clients - see the note there.
    if before:
        all_cases = all_cases.filter(Case.id < before)

    rows = all_cases.order_by(Case.id.desc()).limit(limit + 1).all()

    has_next = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if has_next else None

    return {"items": items, "total": total, "has_next": has_next, "next_cursor": next_cursor}


@cases_router.patch("/cases/{id}", response_model = CaseOut)
def update_case (id: int, new_info: CaseUpdate, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_case = db.query(Case).filter( Case.id == id, owned_by(current_user, Case), Case.deleted_at.is_(None)).first()

    if not current_case: 
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
            )

    if current_case.status == "Closed":
        raise HTTPException(
            status_code = 409,
            detail = "Case is closed"
        )

    data = new_info.model_dump(exclude_unset = True)

    sent_version = data.pop("version", None)

    expected_version = sent_version if sent_version is not None else current_case.version

    assignee_changed = (
        "assignee_id" in data
        and data["assignee_id"] != current_case.assignee_id
    )

    if assignee_changed and data["assignee_id"] is not None:

        assignee = db.query(Staff).filter(
            Staff.id == new_info.assignee_id,
            Staff.deleted_at.is_(None),
        ).first()

        if not assignee:
            raise HTTPException(
                status_code = 404,
                detail = "Assignee not found"
            )

    values = dict(data)
    values["version"] = Case.version + 1

    updated = (
        db.query(Case)
        .filter(Case.id == current_case.id, Case.version == expected_version)
        .update(values, synchronize_session=False)
    )

    if updated == 0:
        db.rollback()
        raise HTTPException(
            status_code = 409,
            detail = "This case was changed by someone else. Reload and try again."
        )

    if assignee_changed:
        db.add(CaseAssignment(
            case_id=current_case.id,
            assignee_id=data["assignee_id"],
            assigned_by_id=current_user.id,
        ))

    db.commit()
    db.refresh(current_case)

    return current_case


@cases_router.patch("/cases/{id}/status", response_model = CaseOut)
def status_update(id: int, new_info: CaseStatusUpdate, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_case = db.query(Case).filter(Case.id == id, owned_by(current_user, Case), Case.deleted_at.is_(None)).first()

    if not current_case:
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
            )

    if new_info.status not in ALLOWED_TRANSITIONS.get(current_case.status, []) :
        raise HTTPException(
            status_code = 409,
            detail = f"Cannot change status from {current_case.status} to {new_info.status}"
            )

    from_status = current_case.status

    updated = (
        db.query(Case)
        .filter(Case.id == current_case.id, Case.status == from_status)
        .update(
            {"status": new_info.status, "version": Case.version + 1},
            synchronize_session=False,
        )
    )

    if updated == 0:
        db.rollback()
        raise HTTPException(
            status_code = 409,
            detail = "This case was changed by someone else. Reload and try again."
        )

    # Updtae History after Update
    db.add(CaseStatusChange(
        case_id=current_case.id,
        from_status=from_status,
        to_status=new_info.status,
        changed_by_id=current_user.id,
    ))

    db.commit()
    db.refresh(current_case)

    return current_case


@cases_router.delete("/cases/{id}", response_model = CaseOut)
def delete_case(id: int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):
   
    current_case = db.query(Case).filter(
        Case.id == id, owned_by(current_user, Case), Case.deleted_at.is_(None)
    ).first()

    if not current_case:
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
        )

    current_case.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_case)

    return current_case
