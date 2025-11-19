from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_current_global_admin
from app.models.user import User
from app.models.competition import Competition
from app.models.participant import JoinRequest, JoinRequestStatus, Participant
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.participant import JoinRequestResponse

router = APIRouter()


@router.get("/join-requests/{competition_id}", response_model=List[JoinRequestResponse])
async def get_join_requests(
    competition_id: str,
    status_filter: Optional[JoinRequestStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get join requests for a competition (admins only)"""
    # Verify competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only competition admins can view join requests",
        )

    # Get join requests
    query = select(JoinRequest).where(JoinRequest.competition_id == competition_id)

    if status_filter:
        query = query.where(JoinRequest.status == status_filter)

    result = await db.execute(query.order_by(JoinRequest.created_at.desc()))
    requests = result.scalars().all()

    return [JoinRequestResponse.model_validate(req) for req in requests]


@router.post("/join-requests/{request_id}/approve")
async def approve_join_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a join request (admins only)"""
    # Get join request
    request_result = await db.execute(
        select(JoinRequest).where(JoinRequest.id == request_id)
    )
    join_request = request_result.scalar_one_or_none()

    if not join_request:
        raise HTTPException(status_code=404, detail="Join request not found")

    # Get competition
    comp_result = await db.execute(
        select(Competition).where(Competition.id == join_request.competition_id)
    )
    competition = comp_result.scalar_one()

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only competition admins can approve join requests",
        )

    # Update join request
    join_request.status = JoinRequestStatus.APPROVED
    join_request.reviewed_by_user_id = current_user.id
    join_request.reviewed_at = datetime.utcnow()

    # Add user as participant
    participant = Participant(
        user_id=join_request.user_id,
        competition_id=join_request.competition_id,
    )
    db.add(participant)

    # Create audit log entry
    audit_log = AuditLog(
        admin_user_id=current_user.id,
        action=AuditAction.JOIN_REQUEST_APPROVED,
        target_type="join_request",
        target_id=join_request.id,
        details={
            "competition_id": str(competition.id),
            "user_id": str(join_request.user_id),
        },
    )
    db.add(audit_log)

    await db.commit()

    return {"message": "Join request approved"}


@router.post("/join-requests/{request_id}/reject")
async def reject_join_request(
    request_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a join request (admins only)"""
    # Get join request
    request_result = await db.execute(
        select(JoinRequest).where(JoinRequest.id == request_id)
    )
    join_request = request_result.scalar_one_or_none()

    if not join_request:
        raise HTTPException(status_code=404, detail="Join request not found")

    # Get competition
    comp_result = await db.execute(
        select(Competition).where(Competition.id == join_request.competition_id)
    )
    competition = comp_result.scalar_one()

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only competition admins can reject join requests",
        )

    # Update join request
    join_request.status = JoinRequestStatus.REJECTED
    join_request.reviewed_by_user_id = current_user.id
    join_request.reviewed_at = datetime.utcnow()
    join_request.rejection_reason = reason

    # Create audit log entry
    audit_log = AuditLog(
        admin_user_id=current_user.id,
        action=AuditAction.JOIN_REQUEST_REJECTED,
        target_type="join_request",
        target_id=join_request.id,
        details={
            "competition_id": str(competition.id),
            "user_id": str(join_request.user_id),
            "reason": reason,
        },
    )
    db.add(audit_log)

    await db.commit()

    return {"message": "Join request rejected"}


@router.get("/audit-logs")
async def get_audit_logs(
    competition_id: Optional[str] = None,
    action_filter: Optional[AuditAction] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs (admins only)"""
    # Build query
    query = select(AuditLog)

    # If not global admin, filter by competitions where user is admin
    if current_user.role != "global_admin":
        # Get competitions where user is admin
        comp_query = select(Competition.id).where(
            Competition.league_admin_ids.contains([str(current_user.id)])
        )
        comp_result = await db.execute(comp_query)
        admin_competition_ids = [str(row[0]) for row in comp_result.all()]

        if not admin_competition_ids:
            return []

        # Filter logs by competitions
        query = query.where(
            and_(
                AuditLog.target_type == "competition",
                AuditLog.target_id.in_(admin_competition_ids),
            )
        )

    # Apply filters
    if competition_id:
        query = query.where(AuditLog.target_id == competition_id)

    if action_filter:
        query = query.where(AuditLog.action == action_filter)

    # Order and paginate
    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "admin_user_id": str(log.admin_user_id),
            "action": log.action,
            "target_type": log.target_type,
            "target_id": str(log.target_id) if log.target_id else None,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
