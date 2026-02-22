from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

class RecordFetchBody(BaseModel):
    destination_url: str
    source_url: str
    request_timestamp: int
    options: Optional[dict] = None

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from collections import Counter
url_lists = Counter()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.post("/record_fetch")
def record_fetch(body: RecordFetchBody):
    if body.destination_url != "/graphql":
        return {"message": "Not a graphql request"}

    print(f"request to: {body.destination_url} from {body.source_url}")
    print(f"options: {body.options.keys()}")
    url_lists[body.destination_url] += 1
    return {"message": "Request recorded"}

@app.get("/get_url_lists")
def get_url_lists():
    return url_lists