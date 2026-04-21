"""Pydantic v2 schemas for ICP module."""

from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime


class ICPBuildRequest(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters.")
        return v.strip()


class ICPCreateRequest(BaseModel):
    name: str
    description: str
    industries: List[str] = []
    job_titles: List[str] = []
    seniority_levels: List[str] = []
    company_sizes: List[str] = []
    locations: List[str] = []
    keywords: List[str] = []
    intent_signals: List[str] = []
    search_queries: List[str] = []


class ICPUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industries: Optional[List[str]] = None
    job_titles: Optional[List[str]] = None
    seniority_levels: Optional[List[str]] = None
    company_sizes: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    intent_signals: Optional[List[str]] = None
    search_queries: Optional[List[str]] = None


class ICPResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    industries: List[str]
    job_titles: List[str]
    seniority_levels: List[str]
    company_sizes: List[str]
    locations: List[str]
    keywords: List[str]
    intent_signals: List[str]
    search_queries: List[str]
    total_leads_generated: int
    total_converted: int
    conversion_rate: float
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ICPListResponse(BaseModel):
    items: List[ICPResponse]
    total: int
