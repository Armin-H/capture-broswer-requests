FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml ./
COPY core/ ./core/
COPY capture/ ./capture/
COPY adapters/ ./adapters/

RUN pip install -e .

CMD ["uvicorn", "capture.ingest_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
