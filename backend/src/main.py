import time
from collections import Counter
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import FetchRecord, MitmHttpCapture, create_tables, get_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

class RecordFetchBody(BaseModel):
    id: str
    destination_url: str
    source_url: str
    request_timestamp: int
    options: Optional[dict] = None


class MitmRequestPart(BaseModel):
    method: str
    url: str
    headers: dict[str, str]
    body: Optional[str] = None


class MitmResponsePart(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: Optional[str] = None


class MitmCaptureCreate(BaseModel):
    request: MitmRequestPart
    response: MitmResponsePart


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


url_lists = Counter()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.post("/record_fetch")
def record_fetch(body: RecordFetchBody, session: Session = Depends(get_session)):
    # if body.destination_url != "/graphql":
    #     return {"message": "Not a graphql request"}

    print(f"request to: {body.destination_url} from {body.source_url}")
    # print(f"options: {body.options.keys()}")
    url_lists[body.destination_url] += 1

    record = FetchRecord(
        client_id=body.id,
        destination_url=body.destination_url,
        source_url=body.source_url,
        request_timestamp=body.request_timestamp,
        options=body.options
    )
    session.add(record)
    session.commit()
    return {"message": "Request recorded", "id": body.id}

@app.patch("/record_fetch/{record_id}/response")
def update_fetch_response(record_id: str, body: dict, session: Session = Depends(get_session)):
    record = session.query(FetchRecord).filter(FetchRecord.client_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    record.response_data = body
    session.commit()
    return {"message": "Response received"}

@app.get("/get_url_lists")
def get_url_lists():
    return url_lists


@app.post("/mitm/captures")
def create_mitm_capture(body: MitmCaptureCreate, session: Session = Depends(get_session)):
    """Persist one JSON HTTP exchange (bodies stored as UTF-8 text)."""
    captured_at_ms = int(time.time() * 1000)
    row = MitmHttpCapture(
        captured_at_ms=captured_at_ms,
        request_method=body.request.method,
        request_url=body.request.url,
        request_headers=body.request.headers,
        request_body=body.request.body,
        response_status_code=body.response.status_code,
        response_headers=body.response.headers,
        response_body=body.response.body,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "message": "Capture recorded",
        "id": row.id,
        "captured_at_ms": row.captured_at_ms,
    }
