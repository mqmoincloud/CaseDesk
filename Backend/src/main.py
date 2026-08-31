from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.config import config

from src.routers import auth_router, client_router, cases_router, notes_router

app = FastAPI()

@app.exception_handler(StarletteHTTPException)
def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {
            "status": exc.status_code,
            "message": exc.detail,
            "fields": {},
        }},
    )

@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    fields = {}
    for err in exc.errors():
        name = err["loc"][-1]  
        fields[name] = err["msg"]

    return JSONResponse(
        status_code=422,
        content={"error": {
            "status": 422,
            "message": "Validation failed",
            "fields": fields,
        }},
    )


@app.exception_handler(Exception)
def unexpected_error(request: Request, exc: Exception):

    return JSONResponse(
        status_code=500,
        content={"error": {
            "status": 500,
            "message": "Something went wrong.",
            "fields": {},
        }},
    )


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

@app.get("/")
def home(db: Session = Depends(get_db)):
    return {"message": "DB Connected !!"}