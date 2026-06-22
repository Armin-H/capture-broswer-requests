"""
Pydantic and ORM models for Seek silver layer.
Uses a separate SilverBase so drop_all never touches bronze tables.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

SilverBase = declarative_base()


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


class Advertiser(SilverBase):
    __tablename__ = "advertisers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)


class Company(SilverBase):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    rating = Column(Float, nullable=True)
    num_reviews = Column(Integer, nullable=True)
    size = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)


class JobListing(SilverBase):
    __tablename__ = "job_listings"

    id = Column(String, primary_key=True)
    fetch_record_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    listed_at = Column(String, nullable=True)
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
