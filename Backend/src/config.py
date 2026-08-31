import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    origin = os.getenv("ORIGIN")
    secret_key = os.getenv("SECRET_KEY")
    db_url = os.getenv("DB_URL")
    algorithm = os.getenv("ALGORITHM")
    token_minutes = int(os.getenv("TOKEN_MINUTES", "30"))


config = Config()

REQUIRED = ["origin", "secret_key", "db_url", "algorithm"]

missing = [name for name in REQUIRED if not getattr(config, name)]

if missing:
    keys = ", ".join(name.upper() for name in missing)
    raise RuntimeError(
        f"Missing from .env: {keys}. Copy .env.example to .env and fill it in."
    )

if config.secret_key == "replace-me-with-a-long-random-string":
    raise RuntimeError(
        "SECRET_KEY is still the .env.example placeholder. Put a real one in .env."
    )
