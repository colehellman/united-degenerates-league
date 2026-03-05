from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.league import League, LeagueName

router = APIRouter()


@router.get("")
async def list_leagues(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available leagues"""
    result = await db.execute(select(League).order_by(League.display_name))
    leagues = result.scalars().all()

    return [
        {
            "id": str(league.id),
            "name": league.name.value if isinstance(league.name, LeagueName) else league.name,
            "display_name": league.display_name,
            "is_team_based": league.is_team_based,
        }
        for league in leagues
    ]
