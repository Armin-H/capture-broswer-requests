"""SQLAlchemy models for the linkedin_jobs Postgres schema."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import declarative_base

from core.db import engine

SCHEMA = "linkedin_jobs"

LinkedInJobsBase = declarative_base()


class JobObservation(LinkedInJobsBase):
    __tablename__ = "job_observation"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    job_id = Column(String, nullable=False, index=True)
    observed_at_ms = Column(BigInteger, nullable=False, index=True)

    title = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    location_label = Column(String, nullable=True)
    listed_at_label = Column(String, nullable=True)
    applicant_count_label = Column(String, nullable=True)
    promoted_label = Column(String, nullable=True)
    application_status_label = Column(String, nullable=True)
    workplace_type_label = Column(String, nullable=True)
    employment_type_label = Column(String, nullable=True)
    is_easy_apply = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=False)


class AboutTheCompanyForJobDetailsObservation(LinkedInJobsBase):
    __tablename__ = "about_the_company_for_job_details_observation"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    job_observation_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.job_observation.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(String, nullable=True)
    followers_label = Column(String, nullable=True)
    industry_label = Column(String, nullable=True)
    size_label = Column(String, nullable=True)
    linkedin_headcount_label = Column(String, nullable=True)
    company_id = Column(String, nullable=True)
    company_url = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)


class ObservationCapture(LinkedInJobsBase):
    __tablename__ = "observation_capture"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    job_observation_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.job_observation.id"),
        nullable=False,
        index=True,
    )
    mitm_capture_id = Column(Integer, nullable=False, index=True)
    section = Column(String, nullable=False)


def create_linkedin_jobs_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    LinkedInJobsBase.metadata.create_all(bind=engine)
