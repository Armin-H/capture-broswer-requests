from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

class RecordFetchBody(BaseModel):
    url: str
    options: Optional[dict] = None

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.post("/record_fetch")
def record_fetch(body: RecordFetchBody):
    print(f"Request made to: {body.url}")
    print(f"Request options: {body.options.keys()}")
    return {"message": "Request recorded"}