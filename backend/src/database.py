import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db_service")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DB_CONNECTION_STRING = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
print(f"{DB_CONNECTION_STRING=}")
engine = create_engine(DB_CONNECTION_STRING)

def get_session():
    with Session(engine) as session:
        yield session

# SessionLocal = sessionmaker(engine)
# with SessionLocal() as session:
#     result = session.execute(text("SELECT 1"))
#     print(result.all())