import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    origin = os.getenv("ORIGIN")
    secret_key = os.getenv("SECRET_KEY")
    db_url = os.getenv("DB_URL")
    algorithm = os.getenv("ALGORITHM")


config = Config()