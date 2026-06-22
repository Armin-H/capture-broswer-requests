"""Single source of truth for database connection."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


load_dotenv(_repo_root() / ".env.sample")


def get_database_url() -> str:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    with Session(engine) as session:
        yield session
