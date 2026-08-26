# from src.models.todo import Todo
# from src.models.client import Client
# from src.models.staff import Staff




from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.database import get_db, Base, engine
from src.config import config
from src.models import Case, Client, Note, Staff

from src.routers import auth_router, client_router, cases_router, notes_router

app = FastAPI()

# This is how we include the different routers into the main FastAPI application.
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(cases_router)
app.include_router(notes_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base.metadata.create_all(bind=engine)

@app.get("/")
def home(db: Session = Depends(get_db)):
    return {"message": "DB Connected Fine !!"}