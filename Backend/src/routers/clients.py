from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, or_
from src.database import get_db, like_term
from src.models import Staff, Client, Case
from src.schemas import ClientOut, ClientRegister, ClientUpdate, ClientPage
from src.security import get_current_user, owned_by
from datetime import datetime, timezone

client_router = APIRouter()


@client_router.post("/clients/registration", response_model = ClientOut)
def client_registration(client: ClientRegister, db: Session = Depends(get_db), current_user : Staff = Depends(get_current_user)):

    if client.staff_id is not None and current_user.role != "admin":
        raise HTTPException(
            status_code = 403,
            detail = "Only an admin can create a client for someone else"
        )

    # Reaching here means either an admin, or no staff_id was sent.
    owner_id = current_user.id

    if current_user.role == "admin" and client.staff_id:
        owner = db.query(Staff).filter(Staff.id == client.staff_id, Staff.deleted_at.is_(None)).first()

        if not owner:
            raise HTTPException(status_code=404, detail="Staff not found")

        owner_id = owner.id

    new_client = Client(
        staff_id = owner_id,
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
def get_all_clients(search: str | None = Query(None, max_length=200), before: int | None = Query(None, ge=1), limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user) ):

    all_clients = db.query(Client).options(
        selectinload(Client.owner)
    ).filter(
        owned_by(current_user, Client) ,
        Client.deleted_at.is_(None)
        )

    if search:
        term = like_term(search)
        all_clients = all_clients.filter(or_(
            func.lower(Client.name).like(term, escape="\\"),
            func.lower(Client.email).like(term, escape="\\"),
            func.lower(Client.phone).like(term, escape="\\")
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
        owned_by(current_user, Client),
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

    client = db.query(Client).filter(id == Client.id, owned_by(current_user, Client), Client.deleted_at.is_(None)).first()

    if not client:
        raise HTTPException(
            status_code = 404,
            detail = "Client Not Exist"
        )

    data = new_info.model_dump(exclude_unset = True)

    if data.get("email"):
        data["email"] = data["email"].lower()

    for key, value in data.items():
        setattr(client, key, value)

    db.commit()
    db.refresh(client)

    return client


@client_router.delete("/clients/{id}", response_model = ClientOut)
def delete_client(id: int, db: Session = Depends(get_db), current_user: Staff = Depends(get_current_user)):

    client = db.query(Client).filter( Client.id == id, owned_by(current_user, Client), Client.deleted_at.is_(None)).first()

    if not client :
         raise HTTPException(
            status_code = 404,
            detail = "Client Not Exist"
        )

    cases = db.query(Case).filter(Case.client_id == client.id, owned_by(current_user, Case), Case.deleted_at.is_(None)).count()

    if cases > 0 :
        raise HTTPException(
                    status_code = 409,
                    detail="Client has active cases"
                )

    client.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(client)

    return client
