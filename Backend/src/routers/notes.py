from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas import NoteRegister, NoteOut
from src.models import Staff, Case, Note
from src.security import case_visible_to, get_current_user
from datetime import datetime, timezone


notes_router =  APIRouter()


@notes_router.post("/cases/{id}/notes", response_model = NoteOut)
def create_note(id: int,note_info: NoteRegister , db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    # Same visibility as reading the case: the owner or the assignee.
    current_case  = db.query(Case).filter(Case.id == id, case_visible_to(current_user), Case.deleted_at.is_(None)).first()

    if not current_case :
        raise HTTPException(
            status_code = 404,
            detail = "Case not found"
            )

    new_note = Note(
        case_id = id,
        staff_id = current_user.id,
        body = note_info.body
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return new_note


@notes_router.delete("/notes/{id}", response_model = NoteOut)
def delete_note(id: int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    # Deliberately owner-only. US-14 says "only notes on cases I own", so an
    # assignee can add a note but cannot remove one.
    current_note = db.query(Note).join(Case).filter(Note.id == id, Case.staff_id == current_user.id, Note.deleted_at.is_(None)).first()

    if not current_note : 
        raise HTTPException(
            status_code = 404,
            detail = "Note not found"
            )

    current_note.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_note)

    return current_note

    




















