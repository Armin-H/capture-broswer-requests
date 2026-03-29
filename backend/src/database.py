import os

from sqlalchemy import BigInteger, Column, Integer, String, Text, create_engine, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, declarative_base

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

Base = declarative_base()

class FetchRecord(Base):

    __tablename__ = "fetch_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True)
    destination_url = Column(String)
    source_url = Column(String)
    request_timestamp = Column(BigInteger)
    options = Column(JSON)
    response_data = Column(JSON, nullable=True)


class MitmHttpCapture(Base):
    """MITM capture when response is JSON (text bodies, metadata only)."""

    __tablename__ = "mitm_http_captures"

    id = Column(Integer, primary_key=True, index=True)
    # When the backend persisted this row (ms since Unix epoch).
    captured_at_ms = Column(BigInteger, nullable=False)

    request_method = Column(String(32), nullable=False)
    request_url = Column(Text, nullable=False)
    request_headers = Column(JSONB, nullable=False)
    request_body = Column(Text, nullable=True)

    response_status_code = Column(Integer, nullable=False)
    response_headers = Column(JSONB, nullable=False)
    response_body = Column(Text, nullable=True)


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created")


# SessionLocal = sessionmaker(engine)
# with SessionLocal() as session:
#     result = session.execute(text("SELECT 1"))
#     print(result.all())
