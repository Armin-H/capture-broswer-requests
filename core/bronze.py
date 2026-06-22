"""Bronze layer ORM models (unchanged schemas)."""

from sqlalchemy import BigInteger, Column, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

from core.db import engine

BronzeBase = declarative_base()


class FetchRecord(BronzeBase):
    __tablename__ = "fetch_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True)
    destination_url = Column(String)
    source_url = Column(String)
    request_timestamp = Column(BigInteger)
    options = Column(JSON)
    response_data = Column(JSON, nullable=True)


class MitmHttpCapture(BronzeBase):
    __tablename__ = "mitm_http_captures"

    id = Column(Integer, primary_key=True, index=True)
    captured_at_ms = Column(BigInteger, nullable=False)

    request_method = Column(String(32), nullable=False)
    request_url = Column(Text, nullable=False)
    request_headers = Column(JSONB, nullable=False)
    request_body = Column(Text, nullable=True)

    response_status_code = Column(Integer, nullable=False)
    response_headers = Column(JSONB, nullable=False)
    response_body = Column(Text, nullable=True)


def create_tables() -> None:
    BronzeBase.metadata.create_all(bind=engine)
