from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional

from app.models.bug_report import BugReportStatus, BugReportCategory


class BugReportCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: BugReportCategory = BugReportCategory.OTHER
    page_url: Optional[str] = Field(None, max_length=500)


class BugReportStatusUpdate(BaseModel):
    status: BugReportStatus


class BugReportResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    title: str
    description: str
    status: BugReportStatus
    category: BugReportCategory
    page_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
