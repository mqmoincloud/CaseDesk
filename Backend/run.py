"""Start CaseDesk with one command.

    python run.py              migrate, seed if empty, serve
    python run.py --reseed     wipe and re-seed first
"""

import subprocess
import sys

import uvicorn

from scripts.seed import seed

HOST = "127.0.0.1"
PORT = 8000


def migrate():
    print("==> Applying migrations")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )


def database_is_empty():
    from src.database import localSession
    from src.models import Staff

    db = localSession()
    try:
        return db.query(Staff).count() == 0
    finally:
        db.close()


def maybe_seed(force):
    if force:
        print("==> Re-seeding (--reseed)")
    elif database_is_empty():
        print("==> Empty database, seeding demo data")
    else:
        print("==> Database already has data, skipping seed (use --reseed to force)")
        return

    seed()


def serve():
    print(f"==> Starting server on http://{HOST}:{PORT}  (docs at /docs)")
    uvicorn.run("src.main:app", host=HOST, port=PORT, reload=True)


if __name__ == "__main__":
    migrate()
    maybe_seed(force="--reseed" in sys.argv)
    serve()
