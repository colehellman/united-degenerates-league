from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class BugReportStatus(str, enum.Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BugReportCategory(str, enum.Enum):
    UI = "ui"
    PERFORMANCE = "performance"
    DATA = "data"
    AUTH = "auth"
    OTHER = "other"


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Who filed the report
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=False)

    status = Column(Enum(BugReportStatus), default=BugReportStatus.OPEN, nullable=False)
    category = Column(Enum(BugReportCategory), default=BugReportCategory.OTHER, nullable=False)

    # Optional: the page URL where the bug was encountered
    page_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bug_reports")
