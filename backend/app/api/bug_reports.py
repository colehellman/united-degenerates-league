from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_current_global_admin
from app.models.user import User
from app.models.bug_report import BugReport
from app.schemas.bug_report import BugReportCreate, BugReportResponse, BugReportStatusUpdate

router = APIRouter()


@router.post("", response_model=BugReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_bug_report(
    data: BugReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a bug report. Any authenticated user can file a report."""
    report = BugReport(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        page_url=data.page_url,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return BugReportResponse.model_validate(report)


@router.get("/mine", response_model=List[BugReportResponse])
async def get_my_bug_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return bug reports filed by the current user, newest first."""
    result = await db.execute(
        select(BugReport)
        .where(BugReport.user_id == current_user.id)
        .order_by(BugReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [BugReportResponse.model_validate(r) for r in reports]


@router.get("", response_model=List[BugReportResponse])
async def list_bug_reports(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return all bug reports (paginated). Global admins only."""
    result = await db.execute(
        select(BugReport)
        .order_by(BugReport.created_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
    )
    reports = result.scalars().all()
    return [BugReportResponse.model_validate(r) for r in reports]


@router.patch("/{report_id}", response_model=BugReportResponse)
async def update_bug_report_status(
    report_id: str,
    update: BugReportStatusUpdate,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a bug report's status. Global admins only."""
    result = await db.execute(select(BugReport).where(BugReport.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug report not found")

    report.status = update.status
    report.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(report)
    return BugReportResponse.model_validate(report)
