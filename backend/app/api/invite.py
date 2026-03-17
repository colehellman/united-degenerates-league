from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_db
from app.models.competition import Competition, CompetitionStatus
from app.models.invite_link import InviteLink
from app.models.participant import Participant
from app.schemas.invite_link import InviteResolveResponse

router = APIRouter()


@router.get("/{token}", response_model=InviteResolveResponse)
async def resolve_invite_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Resolve an invite token to competition info. No auth required."""
    result = await db.execute(
        select(InviteLink)
        .options(joinedload(InviteLink.competition).joinedload(Competition.league))
        .where(InviteLink.token == token)
    )
    invite_link = result.scalar_one_or_none()

    if not invite_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite link not found",
        )

    competition = invite_link.competition

    if competition.status == CompetitionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This competition has already ended",
        )

    count_result = await db.execute(
        select(func.count(Participant.id)).where(Participant.competition_id == competition.id)
    )
    participant_count = count_result.scalar() or 0

    return InviteResolveResponse(
        competition_id=competition.id,
        competition_name=competition.name,
        description=competition.description,
        league_display_name=competition.league.display_name,
        mode=competition.mode,
        status=competition.status,
        participant_count=participant_count,
        max_participants=competition.max_participants,
        is_admin_invite=invite_link.is_admin_invite,
    )
