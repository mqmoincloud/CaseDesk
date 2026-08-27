from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from src.database import get_db
from src.models import Staff, Client, Case
from src.schemas import ClientOut, ClientRegister, ClientUpdate, ClientPage
from src.security import get_current_user
from datetime import datetime, timezone

client_router = APIRouter()


@client_router.post("/clients/registration", response_model = ClientOut)
def client_registration(client: ClientRegister, db: Session = Depends(get_db), current_user : Staff = Depends(get_current_user)):

    new_client = Client(
        staff_id = current_user.id,
        name = client.name,
        email = client.email.lower() if client.email else None,
        phone = client.phone,
        address = client.address
    )

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    return new_client


@client_router.get("/clients", response_model = ClientPage)
def get_all_clients(search: str | None = None, before: int | None = None, limit: int = 10, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user) ):

    all_clients = db.query(Client).filter(
        Client.staff_id == current_user.id ,
        Client.deleted_at.is_(None)
        )

    if search:
        term = f"%{search.lower()}%"
        all_clients = all_clients.filter(or_(
            func.lower(Client.name).like(term),
            func.lower(Client.email).like(term),
            func.lower(Client.phone).like(term)
        ))


    total = all_clients.count()

    if before:
        all_clients = all_clients.filter(Client.id < before)

    # One extra row tells us whether there is another page, without a second query.
    rows = all_clients.order_by(Client.id.desc()).limit(limit + 1).all()

    has_next = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if has_next else None

    return {
        "items": items,
        "total": total,
        "has_next": has_next,
        "next_cursor": next_cursor
    }


@client_router.get("/clients/{id}", response_model = ClientOut)
def get_client(id: int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    current_client = db.query(Client).filter(
        id == Client.id,
        Client.staff_id == current_user.id,
        Client.deleted_at.is_(None)
        ).first()

    if not current_client:
         raise HTTPException(
                    status_code = 404,
                    detail = "Client Not Found"
                )

    return current_client


@client_router.patch("/clients/{id}", response_model = ClientOut)
def update_client(id: int, new_info: ClientUpdate ,db: Session= Depends(get_db), current_user: Staff = Depends(get_current_user)):

    client = db.query(Client).filter(id == Client.id, Client.staff_id == current_user.id, Client.deleted_at.is_(None)).first()

    if not client:
        raise HTTPException(
            status_code = 404,
            detail = "Client Not Exist"
        )

    data = new_info.model_dump(exclude_unset = True)

    for key, value in data.items():
        setattr(client, key, value)

    db.commit()
    db.refresh(client)

    return client


@client_router.delete("/clients/{id}", response_model = ClientOut)
def delete_client(id: int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    client = db.query(Client).filter( Client.id == id, Client.staff_id == current_user.id, Client.deleted_at.is_(None)).first()

    if not client :
         raise HTTPException(
            status_code = 404,
            detail = "Client Not Exist"
        )

    cases = db.query(Case).filter(Case.client_id == client.id, Case.staff_id == current_user.id, Case.deleted_at.is_(None)).count()

    if cases > 0 :
        raise HTTPException(
                    status_code = 409,
                    detail="Client has active cases"
                )

    client.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(client)

    return client 


















