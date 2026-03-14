"""
Pydantic models for silver layer (schema-on-write).
Normalized: advertisers, companies, job_listings.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AdvertiserSilver(BaseModel):
    """Advertiser dimension."""

    id: str
    name: str


class CompanySilver(BaseModel):
    """Company dimension."""

    id: str
    name: str
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None


class JobListingSilver(BaseModel):
    """Job listing with FKs to advertiser and company."""

    id: str
    fetch_record_id: int = Field(..., description="Lineage: FK to fetch_records.id")
    title: str
    status: str
    content: str
    abstract: Optional[str] = None
    listed_at: Optional[datetime] = None
    location_label: Optional[str] = None
    location_area: Optional[str] = None
    location_ids: Optional[list[str]] = None
    classification: Optional[str] = None
    classification_id: Optional[str] = None
    sub_classification: Optional[str] = None
    sub_classification_id: Optional[str] = None
    salary_label: Optional[str] = None
    advertiser_id: str
    advertiser_name: str
    company_id: Optional[str] = None
