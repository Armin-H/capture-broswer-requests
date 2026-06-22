import json

from sqlalchemy import text

from core.db import engine

query = text("""
    SELECT (response_data->>'body')::jsonb
    FROM fetch_records
    WHERE destination_url = '/graphql'
    AND (options->>'body')::jsonb->>'operationName' = 'jobDetailsWithPersonalised';
""")

with engine.connect() as conn:
    results = conn.execute(query).fetchall()

    for i, record in enumerate(results):
        response_data = record[0]
        with open(f"response_data_{i}.json", "w", encoding="utf-8") as f:
            json.dump(response_data, f, ensure_ascii=False, indent=4)
        print(f"Saved response_data_{i}.json")
