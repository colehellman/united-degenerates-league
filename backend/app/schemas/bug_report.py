from datetime import datetime

from pydantic import UUID4, BaseModel, Field

from app.models.bug_report import BugReportCategory, BugReportStatus


class BugReportCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: BugReportCategory = BugReportCategory.OTHER
    page_url: str | None = Field(None, max_length=500)


class BugReportStatusUpdate(BaseModel):
    status: BugReportStatus


class BugReportResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    title: str
    description: str
    status: BugReportStatus
    category: BugReportCategory
    page_url: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
