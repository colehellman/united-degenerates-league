import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_global_admin, get_current_user, get_db
from app.core.limiter import limiter
from app.models.audit_log import AuditAction, AuditLog
from app.models.competition import Competition, CompetitionStatus
from app.models.game import Game, GameStatus
from app.models.participant import JoinRequest, JoinRequestStatus, Participant
from app.models.pick import Pick
from app.models.user import AccountStatus, User, UserRole
from app.schemas.admin import (
    AdminManagement,
    CompetitionStatusChange,
    ScoreCorrectionRequest,
    UserRoleUpdate,
    UserStatusUpdate,
    WinnerDesignationRequest,
)
from app.schemas.participant import JoinRequestResponse, ParticipantWithUserResponse
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: verify competition admin
# ---------------------------------------------------------------------------


async def _require_competition_admin(
    competition_id: str, current_user: User, db: AsyncSession
) -> Competition:
    """Fetch competition and verify the caller is a competition or global admin."""
    result = await db.execute(select(Competition).where(Competition.id == competition_id))
    competition = result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    is_admin = (
        current_user.id in competition.league_admin_ids
        or current_user.role == UserRole.GLOBAL_ADMIN
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Competition admin access required")
    return competition


# ===========================================================================
# USER MANAGEMENT (global admin only)
# ===========================================================================


@router.patch("/users/{user_id}/status", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_user_status(
    request: Request,
    user_id: str,
    update: UserStatusUpdate,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ban, suspend, or reactivate a user account (global admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own account status")

    if target_user.role == UserRole.GLOBAL_ADMIN:
        raise HTTPException(status_code=400, detail="Cannot change status of another global admin")

    old_status = target_user.status.value
    target_user.status = update.status

    # Determine the right audit action based on new status
    action_map = {
        AccountStatus.SUSPENDED: AuditAction.USER_SUSPENDED,
        AccountStatus.BANNED: AuditAction.USER_BANNED,
        AccountStatus.ACTIVE: AuditAction.USER_REACTIVATED,
    }
    audit_action = action_map.get(update.status, AuditAction.USER_SUSPENDED)

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=audit_action,
            target_type="user",
            target_id=target_user.id,
            details={
                "old_status": old_status,
                "new_status": update.status.value,
                "reason": update.reason,
            },
        )
    )

    # Revoke all tokens for suspended/banned users
    if update.status in (AccountStatus.SUSPENDED, AccountStatus.BANNED):
        from app.services.token_blacklist import blacklist_all_user_tokens

        blacklist_all_user_tokens(str(target_user.id))

    await db.commit()
    await db.refresh(target_user)
    return UserResponse.model_validate(target_user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_user_role(
    request: Request,
    user_id: str,
    update: UserRoleUpdate,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role (global admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    old_role = target_user.role.value
    target_user.role = update.role

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.USER_ROLE_CHANGED,
            target_type="user",
            target_id=target_user.id,
            details={"old_role": old_role, "new_role": update.role.value},
        )
    )

    await db.commit()
    await db.refresh(target_user)
    return UserResponse.model_validate(target_user)


@router.get("/users", response_model=list[UserResponse])
async def list_all_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all non-deleted users on the platform (paginated, global admin only)."""
    result = await db.execute(
        select(User)
        .where(User.status != AccountStatus.DELETED)
        .order_by(User.created_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


# ===========================================================================
# COMPETITION STATUS MANAGEMENT
# ===========================================================================


@router.post("/competitions/{competition_id}/status")
@limiter.limit("10/minute")
async def force_competition_status(
    request: Request,
    competition_id: str,
    update: CompetitionStatusChange,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force a competition status change (global admin only).

    Normally, status transitions (UPCOMING → ACTIVE → COMPLETED) are managed
    by background jobs. This endpoint allows global admins to override that
    for exceptional situations like cancellations or early closures.
    """
    result = await db.execute(select(Competition).where(Competition.id == competition_id))
    competition = result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    old_status = competition.status.value
    competition.status = update.status
    competition.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.COMPETITION_STATUS_CHANGED,
            target_type="competition",
            target_id=competition.id,
            details={
                "old_status": old_status,
                "new_status": update.status.value,
                "reason": update.reason,
            },
        )
    )

    await db.commit()
    return {"message": f"Competition status changed from {old_status} to {update.status.value}"}


# ===========================================================================
# SCORE CORRECTION
# ===========================================================================


@router.post("/games/{game_id}/correct-score")
@limiter.limit("5/minute")
async def correct_game_score(
    request: Request,
    game_id: str,
    correction: ScoreCorrectionRequest,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Correct a game's score and re-score all picks (global admin only).

    Limited to one correction per game. After correction, all picks for the
    game are re-scored and participant stats are recalculated.
    """
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.status != GameStatus.FINAL:
        raise HTTPException(status_code=400, detail="Can only correct scores for final games")

    if game.score_correction_count >= 1:
        raise HTTPException(status_code=400, detail="Score has already been corrected once")

    old_home = game.home_team_score
    old_away = game.away_team_score
    old_winner = str(game.winner_team_id) if game.winner_team_id else None

    # Update scores
    game.home_team_score = correction.home_team_score
    game.away_team_score = correction.away_team_score

    # Recalculate winner
    if correction.home_team_score > correction.away_team_score:
        game.winner_team_id = game.home_team_id
    elif correction.away_team_score > correction.home_team_score:
        game.winner_team_id = game.away_team_id
    else:
        game.winner_team_id = None  # Tie

    game.score_corrected_at = datetime.utcnow()
    game.score_correction_count += 1

    # Re-score all picks for this game
    from app.services.score_service import score_picks_for_game

    await score_picks_for_game(db, game)

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.SCORE_CORRECTED,
            target_type="game",
            target_id=game.id,
            details={
                "competition_id": str(game.competition_id),
                "old_home_score": old_home,
                "old_away_score": old_away,
                "old_winner_team_id": old_winner,
                "new_home_score": correction.home_team_score,
                "new_away_score": correction.away_team_score,
                "new_winner_team_id": str(game.winner_team_id) if game.winner_team_id else None,
                "reason": correction.reason,
            },
        )
    )

    await db.commit()
    return {
        "message": "Score corrected and picks re-scored",
        "old_score": f"{old_home}-{old_away}",
        "new_score": f"{correction.home_team_score}-{correction.away_team_score}",
    }


@router.post("/games/{game_id}/rescore")
@limiter.limit("10/minute")
async def rescore_game(
    request: Request,
    game_id: str,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually re-score all picks for a game (global admin only).

    Useful if the scoring job failed or was interrupted. Does not change the
    game's score — just re-evaluates picks against the existing winner.
    """
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.status != GameStatus.FINAL:
        raise HTTPException(status_code=400, detail="Can only re-score final games")

    from app.services.score_service import score_picks_for_game

    await score_picks_for_game(db, game)
    await db.commit()

    return {"message": f"Re-scored picks for game {game_id}"}


# ===========================================================================
# WINNER DESIGNATION
# ===========================================================================


@router.post("/competitions/{competition_id}/winner")
async def designate_winner(
    competition_id: str,
    body: WinnerDesignationRequest,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Designate a competition winner (global admin only).

    Used for tie-breaker scenarios or manual override. The winner must be a
    participant in the competition.
    """
    result = await db.execute(select(Competition).where(Competition.id == competition_id))
    competition = result.scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")

    # Verify the winner is a participant
    participant_check = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == body.winner_user_id,
            )
        )
    )
    if not participant_check.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Winner must be a participant in the competition"
        )

    old_winner = str(competition.winner_user_id) if competition.winner_user_id else None
    competition.winner_user_id = body.winner_user_id
    competition.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.WINNER_DESIGNATED,
            target_type="competition",
            target_id=competition.id,
            details={
                "old_winner_user_id": old_winner,
                "new_winner_user_id": str(body.winner_user_id),
                "reason": body.reason,
            },
        )
    )

    await db.commit()
    return {"message": "Winner designated", "winner_user_id": str(body.winner_user_id)}


# ===========================================================================
# PARTICIPANT MANAGEMENT
# ===========================================================================


@router.delete("/competitions/{competition_id}/participants/{user_id}")
async def remove_participant(
    competition_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a participant from a competition (competition admin or global admin)."""
    competition = await _require_competition_admin(competition_id, current_user, db)

    # Find the participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == user_id,
            )
        )
    )
    participant = participant_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Don't allow removing the competition creator
    if str(competition.creator_id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the competition creator")

    await db.delete(participant)

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.PARTICIPANT_REMOVED,
            target_type="competition",
            target_id=competition.id,
            details={
                "removed_user_id": user_id,
            },
        )
    )

    await db.commit()
    return {"message": "Participant removed"}


@router.get(
    "/competitions/{competition_id}/participants", response_model=list[ParticipantWithUserResponse]
)
async def list_competition_participants(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all participants in a competition with user details (competition admin or global admin)."""
    await _require_competition_admin(competition_id, current_user, db)

    rows_result = await db.execute(
        select(Participant, User)
        .join(User, Participant.user_id == User.id)
        .where(Participant.competition_id == competition_id)
        .order_by(Participant.total_points.desc())
    )
    rows = rows_result.all()

    return [
        ParticipantWithUserResponse(
            id=p.id,
            user_id=p.user_id,
            username=u.username,
            joined_at=p.joined_at,
            total_points=p.total_points,
            total_wins=p.total_wins,
            total_losses=p.total_losses,
            accuracy_percentage=p.accuracy_percentage,
            current_streak=p.current_streak,
        )
        for p, u in rows
    ]


# ===========================================================================
# COMPETITION ADMIN MANAGEMENT
# ===========================================================================


@router.post("/competitions/{competition_id}/admins")
async def add_competition_admin(
    competition_id: str,
    body: AdminManagement,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a user as a competition admin (competition admin or global admin)."""
    competition = await _require_competition_admin(competition_id, current_user, db)

    # Verify the user exists and is a participant
    user_result = await db.execute(select(User).where(User.id == body.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.user_id in competition.league_admin_ids:
        raise HTTPException(status_code=400, detail="User is already a competition admin")

    # Mutate the list (SQLAlchemy needs a new list assigned to detect the change)
    competition.league_admin_ids = [*competition.league_admin_ids, body.user_id]
    competition.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.ADMIN_ADDED,
            target_type="competition",
            target_id=competition.id,
            details={"added_user_id": str(body.user_id)},
        )
    )

    await db.commit()
    return {"message": "Admin added", "user_id": str(body.user_id)}


@router.delete("/competitions/{competition_id}/admins/{admin_user_id}")
async def remove_competition_admin(
    competition_id: str,
    admin_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from competition admin list (competition admin or global admin)."""
    competition = await _require_competition_admin(competition_id, current_user, db)

    # Prevent removing the creator
    if str(competition.creator_id) == admin_user_id:
        raise HTTPException(
            status_code=400, detail="Cannot remove the competition creator as admin"
        )

    import uuid as uuid_mod

    try:
        target_uuid = uuid_mod.UUID(admin_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID") from None

    if target_uuid not in competition.league_admin_ids:
        raise HTTPException(status_code=404, detail="User is not a competition admin")

    competition.league_admin_ids = [
        uid for uid in competition.league_admin_ids if uid != target_uuid
    ]
    competition.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.ADMIN_REMOVED,
            target_type="competition",
            target_id=competition.id,
            details={"removed_user_id": admin_user_id},
        )
    )

    await db.commit()
    return {"message": "Admin removed", "user_id": admin_user_id}


# ===========================================================================
# JOIN REQUESTS
# ===========================================================================


@router.get("/join-requests/{competition_id}", response_model=list[JoinRequestResponse])
async def get_join_requests(
    competition_id: str,
    status_filter: JoinRequestStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get join requests for a competition (admins only)."""
    await _require_competition_admin(competition_id, current_user, db)

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
    """Approve a join request (admins only)."""
    request_result = await db.execute(select(JoinRequest).where(JoinRequest.id == request_id))
    join_request = request_result.scalar_one_or_none()
    if not join_request:
        raise HTTPException(status_code=404, detail="Join request not found")

    if join_request.status != JoinRequestStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Join request is not pending (status: {join_request.status})",
        )

    competition = await _require_competition_admin(
        str(join_request.competition_id), current_user, db
    )

    join_request.status = JoinRequestStatus.APPROVED
    join_request.reviewed_by_user_id = current_user.id
    join_request.reviewed_at = datetime.utcnow()

    participant = Participant(
        user_id=join_request.user_id,
        competition_id=join_request.competition_id,
    )
    db.add(participant)

    db.add(
        AuditLog(
            admin_user_id=current_user.id,
            action=AuditAction.JOIN_REQUEST_APPROVED,
            target_type="join_request",
            target_id=join_request.id,
            details={
                "competition_id": str(competition.id),
                "user_id": str(join_request.user_id),
            },
        )
    )

    await db.commit()
    return {"message": "Join request approved"}


@router.post("/join-requests/{request_id}/reject")
async def reject_join_request(
    request_id: str,
    reason: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a join request (admins only)."""
    request_result = await db.execute(select(JoinRequest).where(JoinRequest.id == request_id))
    join_request = request_result.scalar_one_or_none()
    if not join_request:
        raise HTTPException(status_code=404, detail="Join request not found")

    competition = await _require_competition_admin(
        str(join_request.competition_id), current_user, db
    )

    join_request.status = JoinRequestStatus.REJECTED
    join_request.reviewed_by_user_id = current_user.id
    join_request.reviewed_at = datetime.utcnow()
    join_request.rejection_reason = reason

    db.add(
        AuditLog(
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
    )

    await db.commit()
    return {"message": "Join request rejected"}


# ===========================================================================
# GAME SYNC
# ===========================================================================


@router.post("/sync-games")
async def force_sync_games(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_global_admin),
):
    """Trigger an immediate game sync from ESPN (global admins only)."""
    from app.services.background_jobs import sync_games_from_api

    background_tasks.add_task(sync_games_from_api)
    return {"message": "Game sync triggered"}


# ===========================================================================
# AUDIT LOGS
# ===========================================================================


@router.get("/audit-logs")
async def get_audit_logs(
    competition_id: str | None = None,
    action_filter: AuditAction | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs (admins only)."""
    query = select(AuditLog)

    if current_user.role != UserRole.GLOBAL_ADMIN:
        comp_query = select(Competition.id).where(
            Competition.league_admin_ids.contains([current_user.id])
        )
        comp_result = await db.execute(comp_query)
        admin_competition_ids = [str(row[0]) for row in comp_result.all()]

        if not admin_competition_ids:
            return []

        query = query.where(
            and_(
                AuditLog.target_type == "competition",
                AuditLog.target_id.in_(admin_competition_ids),
            )
        )

    if competition_id:
        query = query.where(AuditLog.target_id == competition_id)

    if action_filter:
        query = query.where(AuditLog.action == action_filter)

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


# ===========================================================================
# PLATFORM ANALYTICS (global admin only)
# ===========================================================================


@router.get("/stats")
async def platform_stats(
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Basic platform analytics (global admin only)."""
    total_users = await db.scalar(
        select(func.count()).select_from(User).where(User.status != AccountStatus.DELETED)
    )
    active_competitions = await db.scalar(
        select(func.count())
        .select_from(Competition)
        .where(Competition.status == CompetitionStatus.ACTIVE)
    )
    total_competitions = await db.scalar(select(func.count()).select_from(Competition))
    total_picks = await db.scalar(select(func.count()).select_from(Pick))
    total_games = await db.scalar(select(func.count()).select_from(Game))

    return {
        "total_users": total_users or 0,
        "active_competitions": active_competitions or 0,
        "total_competitions": total_competitions or 0,
        "total_picks": total_picks or 0,
        "total_games": total_games or 0,
    }


# ===========================================================================
# GLOBAL ADMIN — ALL COMPETITIONS VISIBILITY
# ===========================================================================


@router.get("/competitions")
async def list_all_competitions(
    status_filter: CompetitionStatus | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all competitions with participant counts (global admin only)."""
    query = (
        select(
            Competition,
            func.count(Participant.id).label("participant_count"),
        )
        .outerjoin(Participant, Competition.id == Participant.competition_id)
        .group_by(Competition.id)
    )

    if status_filter:
        query = query.where(Competition.status == status_filter)

    query = query.order_by(Competition.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(comp.id),
            "name": comp.name,
            "status": comp.status.value,
            "mode": comp.mode.value,
            "creator_id": str(comp.creator_id),
            "participant_count": count,
            "start_date": comp.start_date,
            "end_date": comp.end_date,
            "created_at": comp.created_at,
        }
        for comp, count in rows
    ]
