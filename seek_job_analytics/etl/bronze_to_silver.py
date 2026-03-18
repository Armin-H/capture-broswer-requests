"""
Bronze → Silver ETL: Extract from fetch_records, transform with Pydantic, load to silver tables.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env.sample")

from seek_job_analytics.models.silver import (
    AdvertiserSilver,
    CompanySilver,
    JobListingSilver,
)

# --- DB config ---
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Silver table definitions ---
class Advertiser(Base):
    __tablename__ = "advertisers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    rating = Column(Float, nullable=True)
    num_reviews = Column(Integer, nullable=True)
    size = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(String, primary_key=True)
    fetch_record_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    listed_at = Column(String, nullable=True)  # ISO string for simplicity
    location_label = Column(String, nullable=True)
    location_area = Column(String, nullable=True)
    location_ids = Column(JSON, nullable=True)
    classification = Column(String, nullable=True)
    classification_id = Column(String, nullable=True)
    sub_classification = Column(String, nullable=True)
    sub_classification_id = Column(String, nullable=True)
    salary_label = Column(String, nullable=True)
    advertiser_id = Column(String, ForeignKey("advertisers.id"), nullable=False)
    advertiser_name = Column(String, nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)


def extract():
    """Read raw job listing JSON from fetch_records (bronze). Returns (fetch_record_id, body)."""
    query = text("""
        SELECT id, (response_data->>'body')::jsonb AS body
        FROM fetch_records
        WHERE destination_url = '/graphql'
        AND (options->>'body')::jsonb->>'operationName' in ('jobDetails', 'jobDetailsWithPersonalised')
        AND response_data IS NOT NULL
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [(row[0], row[1]) for row in rows]


def _safe_get(data: dict, *keys, default=None):
    """Navigate nested dict; return default if any key missing."""
    for key in keys:
        if data is None or not isinstance(data, dict):
            return default
        data = data.get(key)
    return data if data is not None else default


def transform(fetch_record_id: int, raw: dict) -> tuple[AdvertiserSilver | None, CompanySilver | None, JobListingSilver]:
    """Transform raw JSON to validated Pydantic models."""
    job_details = _safe_get(raw, "data", "jobDetails")
    if not job_details:
        raise ValueError("Missing data.jobDetails in raw JSON")

    job = _safe_get(job_details, "job")
    company_profile = _safe_get(job_details, "companyProfile")

    if not job:
        raise ValueError("Missing job in jobDetails")

    # Advertiser (always present on job)
    advertiser = _safe_get(job, "advertiser")
    advertiser_silver = None
    if advertiser:
        advertiser_silver = AdvertiserSilver(
            id=str(advertiser.get("id", "")),
            name=advertiser.get("name", ""),
        )

    # Company (may be null)
    company_silver = None
    if company_profile:
        overview = _safe_get(company_profile, "overview")
        reviews = _safe_get(company_profile, "reviewsSummary", "overallRating")
        company_silver = CompanySilver(
            id=str(company_profile.get("id", "")),
            name=company_profile.get("name", ""),
            rating=_safe_get(reviews, "value") if reviews else None,
            num_reviews=_safe_get(reviews, "numberOfReviews", "value") if reviews else None,
            size=_safe_get(overview, "size", "description") if overview else None,
            industry=_safe_get(overview, "industry") if overview else None,
            website=_safe_get(overview, "website", "url") if overview else None,
        )

    # Job listing
    tracking = _safe_get(job, "tracking")
    location_info = _safe_get(tracking, "locationInfo") if tracking else None
    classification_info = _safe_get(tracking, "classificationInfo") if tracking else None

    listed_at_raw = _safe_get(job, "listedAt", "dateTimeUtc")
    salary_label = _safe_get(job, "salary", "label") if _safe_get(job, "salary") else None

    job_silver = JobListingSilver(
        id=str(job.get("id", "")),
        fetch_record_id=fetch_record_id,
        title=job.get("title", ""),
        status=job.get("status", ""),
        content=job.get("content", ""),
        abstract=job.get("abstract"),
        listed_at=listed_at_raw,  # Pydantic will parse ISO string to datetime
        location_label=_safe_get(job, "location", "label"),
        location_area=_safe_get(location_info, "area") if location_info else None,
        location_ids=_safe_get(location_info, "locationIds") if location_info else None,
        classification=_safe_get(classification_info, "classification") if classification_info else None,
        classification_id=_safe_get(classification_info, "classificationId") if classification_info else None,
        sub_classification=_safe_get(classification_info, "subClassification") if classification_info else None,
        sub_classification_id=_safe_get(classification_info, "subClassificationId") if classification_info else None,
        salary_label=salary_label,
        advertiser_id=str(advertiser.get("id", "")) if advertiser else "",
        advertiser_name=advertiser.get("name", "") if advertiser else "",
        company_id=str(company_profile.get("id", "")) if company_profile else None,
    )

    return advertiser_silver, company_silver, job_silver


def load(records: list[tuple[AdvertiserSilver | None, CompanySilver | None, JobListingSilver]]):
    """Load validated records into silver tables. Drops and recreates all tables, then inserts fresh data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Deduplicate advertisers and companies (same entity can appear in multiple job records)
    advertisers: dict[str, AdvertiserSilver] = {}
    companies: dict[str, CompanySilver] = {}
    for advertiser, company, job in records:
        if advertiser and advertiser.id not in advertisers:
            advertisers[advertiser.id] = advertiser
        if company and company.id not in companies:
            companies[company.id] = company

    with SessionLocal() as session:
        for advertiser in advertisers.values():
            session.add(Advertiser(id=advertiser.id, name=advertiser.name))
        for company in companies.values():
            session.add(
                Company(
                    id=company.id,
                    name=company.name,
                    rating=company.rating,
                    num_reviews=company.num_reviews,
                    size=company.size,
                    industry=company.industry,
                    website=company.website,
                )
            )
        for _, _, job in records:
            session.add(
                JobListing(
                    id=job.id,
                    fetch_record_id=job.fetch_record_id,
                    title=job.title,
                    status=job.status,
                    content=job.content,
                    abstract=job.abstract,
                    listed_at=job.listed_at.isoformat() if job.listed_at else None,
                    location_label=job.location_label,
                    location_area=job.location_area,
                    location_ids=job.location_ids,
                    classification=job.classification,
                    classification_id=job.classification_id,
                    sub_classification=job.sub_classification,
                    sub_classification_id=job.sub_classification_id,
                    salary_label=job.salary_label,
                    advertiser_id=job.advertiser_id,
                    advertiser_name=job.advertiser_name,
                    company_id=job.company_id,
                )
            )
        session.commit()


def run():
    """Run the full bronze_to_silver pipeline."""
    rows = extract()
    if not rows:
        print("No records to process.")
        return

    records = []
    for fetch_record_id, body in rows:
        try:
            # body may be dict (from jsonb) or need parsing
            raw = body if isinstance(body, dict) else json.loads(body)
            records.append(transform(fetch_record_id, raw))
        except Exception as e:
            print(f"Skipping fetch_record_id={fetch_record_id}: {e}")
            continue

    load(records)
    print(f"Loaded {len(records)} job listings to silver.")


if __name__ == "__main__":
    run()

