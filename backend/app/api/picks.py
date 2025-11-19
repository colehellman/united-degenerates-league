from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.pick import Pick, FixedTeamSelection
from app.models.game import Game, GameStatus
from app.models.competition import Competition, CompetitionMode
from app.models.participant import Participant
from app.schemas.pick import (
    PickCreate,
    PickUpdate,
    PickResponse,
    FixedTeamSelectionCreate,
    FixedTeamSelectionResponse,
)

router = APIRouter()


@router.post("/{competition_id}/daily", response_model=PickResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_pick(
    competition_id: str,
    pick_data: PickCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a daily pick for a game"""
    # Verify competition exists and is Daily Picks mode
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition or competition.mode != CompetitionMode.DAILY_PICKS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found or not in Daily Picks mode",
        )

    # Verify user is participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this competition",
        )

    # Get game
    game_result = await db.execute(
        select(Game).where(Game.id == pick_data.game_id)
    )
    game = game_result.scalar_one_or_none()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Check if game has started (locked)
    if datetime.utcnow() >= game.scheduled_start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game has already started - picks are locked",
        )

    # Check if pick already exists
    existing_pick_result = await db.execute(
        select(Pick).where(
            and_(
                Pick.user_id == current_user.id,
                Pick.competition_id == competition.id,
                Pick.game_id == game.id,
            )
        )
    )
    existing_pick = existing_pick_result.scalar_one_or_none()

    if existing_pick:
        # Update existing pick
        existing_pick.predicted_winner_team_id = pick_data.predicted_winner_team_id
        existing_pick.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_pick)
        return PickResponse.model_validate(existing_pick)

    # Check daily pick limit
    if competition.max_picks_per_day:
        # Count picks for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

        picks_today_result = await db.execute(
            select(func.count(Pick.id)).where(
                and_(
                    Pick.user_id == current_user.id,
                    Pick.competition_id == competition.id,
                    Pick.created_at >= today_start,
                    Pick.created_at <= today_end,
                )
            )
        )
        picks_today = picks_today_result.scalar()

        if picks_today >= competition.max_picks_per_day:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily pick limit ({competition.max_picks_per_day}) reached",
            )

    # Create new pick
    pick = Pick(
        user_id=current_user.id,
        competition_id=competition.id,
        game_id=game.id,
        predicted_winner_team_id=pick_data.predicted_winner_team_id,
    )

    db.add(pick)

    # Update participant last_pick_at
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    participant = participant_result.scalar_one()
    participant.last_pick_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pick)

    return PickResponse.model_validate(pick)


@router.get("/{competition_id}/daily", response_model=List[PickResponse])
async def get_user_daily_picks(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's daily picks for a competition"""
    result = await db.execute(
        select(Pick).where(
            and_(
                Pick.user_id == current_user.id,
                Pick.competition_id == competition_id,
            )
        )
    )
    picks = result.scalars().all()

    return [PickResponse.model_validate(pick) for pick in picks]


@router.post("/{competition_id}/fixed-teams", response_model=FixedTeamSelectionResponse, status_code=status.HTTP_201_CREATED)
async def create_fixed_team_selection(
    competition_id: str,
    selection_data: FixedTeamSelectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a fixed team/golfer selection"""
    # Verify competition exists and is Fixed Teams mode
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition or competition.mode != CompetitionMode.FIXED_TEAMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found or not in Fixed Teams mode",
        )

    # Check if selection phase is still open
    if datetime.utcnow() >= competition.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selection phase has ended",
        )

    # Verify user is participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this competition",
        )

    # Check if team/golfer is already selected by another user (exclusivity)
    if selection_data.team_id:
        existing_selection = await db.execute(
            select(FixedTeamSelection).where(
                and_(
                    FixedTeamSelection.competition_id == competition.id,
                    FixedTeamSelection.team_id == selection_data.team_id,
                )
            )
        )
        if existing_selection.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This team has already been selected by another participant",
            )

    if selection_data.golfer_id:
        existing_selection = await db.execute(
            select(FixedTeamSelection).where(
                and_(
                    FixedTeamSelection.competition_id == competition.id,
                    FixedTeamSelection.golfer_id == selection_data.golfer_id,
                )
            )
        )
        if existing_selection.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This golfer has already been selected by another participant",
            )

    # Check max selections limit
    user_selections_count = await db.execute(
        select(func.count(FixedTeamSelection.id)).where(
            and_(
                FixedTeamSelection.user_id == current_user.id,
                FixedTeamSelection.competition_id == competition.id,
            )
        )
    )
    count = user_selections_count.scalar()

    max_selections = competition.max_teams_per_participant or competition.max_golfers_per_participant
    if max_selections and count >= max_selections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum selections ({max_selections}) reached",
        )

    # Create selection
    selection = FixedTeamSelection(
        user_id=current_user.id,
        competition_id=competition.id,
        team_id=selection_data.team_id,
        golfer_id=selection_data.golfer_id,
    )

    db.add(selection)
    await db.commit()
    await db.refresh(selection)

    return FixedTeamSelectionResponse.model_validate(selection)


@router.get("/{competition_id}/fixed-teams", response_model=List[FixedTeamSelectionResponse])
async def get_user_fixed_team_selections(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's fixed team/golfer selections"""
    result = await db.execute(
        select(FixedTeamSelection).where(
            and_(
                FixedTeamSelection.user_id == current_user.id,
                FixedTeamSelection.competition_id == competition_id,
            )
        )
    )
    selections = result.scalars().all()

    return [FixedTeamSelectionResponse.model_validate(sel) for sel in selections]
