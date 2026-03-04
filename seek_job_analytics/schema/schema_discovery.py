import sys
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pprint import pprint
from genson import SchemaBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env.sample")
print(f"{PROJECT_ROOT=}")


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DB_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print(f"{DB_URL=}")

engine = create_engine(DB_URL)
query = text("""
    SELECT (response_data->>'body')::jsonb
    FROM fetch_records 
    WHERE destination_url = '/graphql'
    AND (options->>'body')::jsonb->>'operationName' = 'jobDetailsWithPersonalised';
""")

builder = SchemaBuilder()


with engine.connect() as conn:
    results = conn.execute(query).fetchall()

    # response_data = results[0][0]
    # print(type(response_data))
    # print(response_data.keys())
    # pprint(response_data)

    for record in results:
        response_data = record[0]
        # print(response_data)
        # break
        builder.add_object(response_data)

    # print(builder.to_schema())
    print(builder.to_json(indent=2))



