from typing import Optional
from collections import Counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from contextlib import asynccontextmanager
from database import create_tables, get_session, FetchRecord
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException


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