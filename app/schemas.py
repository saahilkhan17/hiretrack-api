"""Pydantic v2 request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import AppStatus


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    job_url: str | None = Field(default=None, max_length=500)
    status: AppStatus = AppStatus.wishlist
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    job_url: str | None = Field(default=None, max_length=500)
    status: AppStatus | None = None
    notes: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: str | None
    job_url: str | None
    status: AppStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedApplications(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ApplicationOut]


class StatusSummary(BaseModel):
    status: AppStatus
    count: int
