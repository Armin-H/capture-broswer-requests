from typing import Optional
from collections import Counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from contextlib import asynccontextmanager
from database import create_tables, get_session, FetchRecord
from sqlalchemy.orm import Session
from fastapi import Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

class RecordFetchBody(BaseModel):
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
        destination_url=body.destination_url,
        source_url=body.source_url,
        request_timestamp=body.request_timestamp,
        options=body.options
    )
    session.add(record)
    session.commit()

    return {"message": "Request recorded"}

@app.get("/get_url_lists")
def get_url_lists():
    return url_lists