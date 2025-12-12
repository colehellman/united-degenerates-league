from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.pick import Pick, FixedTeamSelection
from app.models.game import Game, GameStatus
from app.models.competition import Competition, CompetitionMode
from app.models.participant import Participant
from app.schemas.pick import (
    PickCreate,
    PickBatchCreate,
    PickUpdate,
    PickResponse,
    FixedTeamSelectionCreate,
    FixedTeamSelectionBatchCreate,
    FixedTeamSelectionResponse,
)

router = APIRouter()


@router.post("/{competition_id}/daily", response_model=List[PickResponse], status_code=status.HTTP_201_CREATED)
async def create_daily_picks_batch(
    competition_id: str,
    pick_data: PickBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create daily picks for multiple games"""
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
    participant = participant_result.scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this competition",
        )

    created_picks = []
    now = datetime.utcnow()

    # Process each pick in the batch
    for pick_item in pick_data.picks:
        # Get game
        game_result = await db.execute(
            select(Game).where(Game.id == pick_item.game_id)
        )
        game = game_result.scalar_one_or_none()

        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game {pick_item.game_id} not found",
            )

        # Check if game has started (locked)
        if now >= game.scheduled_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Game {game.id} has already started - picks are locked",
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
            existing_pick.predicted_winner_team_id = pick_item.predicted_winner_team_id
            existing_pick.updated_at = now
            created_picks.append(existing_pick)
        else:
            # Create new pick
            pick = Pick(
                user_id=current_user.id,
                competition_id=competition.id,
                game_id=game.id,
                predicted_winner_team_id=pick_item.predicted_winner_team_id,
            )
            db.add(pick)
            created_picks.append(pick)

    # Update participant last_pick_at
    participant.last_pick_at = now

    await db.commit()

    # Refresh all picks
    for pick in created_picks:
        await db.refresh(pick)

    return [PickResponse.model_validate(pick) for pick in created_picks]


@router.get("/{competition_id}/my-picks", response_model=List[PickResponse])
async def get_user_daily_picks(
    competition_id: str,
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD format)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's daily picks for a competition"""
    query = select(Pick).where(
        and_(
            Pick.user_id == current_user.id,
            Pick.competition_id == competition_id,
        )
    )

    # Filter by date if provided
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(
                and_(
                    Pick.created_at >= start_of_day,
                    Pick.created_at <= end_of_day,
                )
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )

    result = await db.execute(query)
    picks = result.scalars().all()

    return [PickResponse.model_validate(pick) for pick in picks]


@router.post("/{competition_id}/fixed-teams", response_model=List[FixedTeamSelectionResponse], status_code=status.HTTP_201_CREATED)
async def create_fixed_team_selections_batch(
    competition_id: str,
    selection_data: FixedTeamSelectionBatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create fixed team/golfer selections (batch)"""
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

    # Get current user's selection count
    user_selections_count = await db.execute(
        select(func.count(FixedTeamSelection.id)).where(
            and_(
                FixedTeamSelection.user_id == current_user.id,
                FixedTeamSelection.competition_id == competition.id,
            )
        )
    )
    current_count = user_selections_count.scalar()

    max_selections = competition.max_teams_per_participant or competition.max_golfers_per_participant
    if max_selections and (current_count + len(selection_data.selections)) > max_selections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum selections ({max_selections}) would be exceeded",
        )

    created_selections = []

    # Process each selection in the batch
    for selection_item in selection_data.selections:
        # Check if team/golfer is already selected by another user (exclusivity)
        if selection_item.team_id:
            existing_selection = await db.execute(
                select(FixedTeamSelection).where(
                    and_(
                        FixedTeamSelection.competition_id == competition.id,
                        FixedTeamSelection.team_id == selection_item.team_id,
                    )
                )
            )
            if existing_selection.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team {selection_item.team_id} has already been selected",
                )

        if selection_item.golfer_id:
            existing_selection = await db.execute(
                select(FixedTeamSelection).where(
                    and_(
                        FixedTeamSelection.competition_id == competition.id,
                        FixedTeamSelection.golfer_id == selection_item.golfer_id,
                    )
                )
            )
            if existing_selection.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Golfer {selection_item.golfer_id} has already been selected",
                )

        # Create selection
        selection = FixedTeamSelection(
            user_id=current_user.id,
            competition_id=competition.id,
            team_id=selection_item.team_id,
            golfer_id=selection_item.golfer_id,
        )
        db.add(selection)
        created_selections.append(selection)

    await db.commit()

    # Refresh all selections
    for selection in created_selections:
        await db.refresh(selection)

    return [FixedTeamSelectionResponse.model_validate(sel) for sel in created_selections]


@router.get("/{competition_id}/my-fixed-selections", response_model=List[FixedTeamSelectionResponse])
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
