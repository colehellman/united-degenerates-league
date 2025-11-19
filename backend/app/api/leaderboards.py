from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.competition import Competition
from app.models.participant import Participant
from app.schemas.participant import LeaderboardEntry

router = APIRouter()


@router.get("/{competition_id}", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    competition_id: str,
    sort_by: str = Query("points", regex="^(points|accuracy|wins|streak)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get leaderboard for a competition"""
    # Verify competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=404,
            detail="Competition not found",
        )

    # Get all participants with user data
    query = (
        select(Participant, User)
        .join(User, Participant.user_id == User.id)
        .where(Participant.competition_id == competition_id)
    )

    # Sort based on query parameter
    if sort_by == "points":
        query = query.order_by(Participant.total_points.desc())
    elif sort_by == "accuracy":
        query = query.order_by(Participant.accuracy_percentage.desc())
    elif sort_by == "wins":
        query = query.order_by(Participant.total_wins.desc())
    elif sort_by == "streak":
        query = query.order_by(Participant.current_streak.desc())

    result = await db.execute(query)
    participants = result.all()

    # Build leaderboard entries
    leaderboard = []
    rank = 1
    for participant, user in participants:
        entry = LeaderboardEntry(
            rank=rank,
            user_id=participant.user_id,
            username=user.username,
            total_points=participant.total_points,
            total_wins=participant.total_wins,
            total_losses=participant.total_losses,
            accuracy_percentage=participant.accuracy_percentage,
            current_streak=participant.current_streak,
            is_current_user=(participant.user_id == current_user.id),
        )
        leaderboard.append(entry)
        rank += 1

    return leaderboard
