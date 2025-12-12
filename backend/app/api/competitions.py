from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_current_global_admin
from app.models.user import User
from app.models.competition import Competition, CompetitionStatus, Visibility
from app.models.participant import Participant, JoinRequest, JoinRequestStatus
from app.models.game import Game
from app.models.league import Team, Golfer
from app.models.pick import FixedTeamSelection
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionResponse,
    CompetitionUpdate,
    CompetitionListResponse,
)
from app.schemas.participant import JoinRequestCreate, JoinRequestResponse

router = APIRouter()


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
async def create_competition(
    competition_data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new competition"""
    # Validate dates
    if competition_data.end_date <= competition_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Create competition
    competition = Competition(
        **competition_data.model_dump(),
        creator_id=current_user.id,
        league_admin_ids=[str(current_user.id)],  # Creator is default admin
        status=CompetitionStatus.UPCOMING,
    )

    db.add(competition)
    await db.commit()
    await db.refresh(competition)

    # Automatically add creator as participant
    participant = Participant(
        user_id=current_user.id,
        competition_id=competition.id,
    )
    db.add(participant)
    await db.commit()

    response = CompetitionResponse.model_validate(competition)
    response.participant_count = 1
    response.user_is_participant = True
    response.user_is_admin = True

    return response


@router.get("", response_model=List[CompetitionListResponse])
async def list_competitions(
    status_filter: Optional[CompetitionStatus] = None,
    visibility: Optional[Visibility] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all competitions accessible to the current user"""
    query = select(Competition)

    # Filter by status if provided
    if status_filter:
        query = query.where(Competition.status == status_filter)

    # Filter by visibility
    if visibility:
        query = query.where(Competition.visibility == visibility)
    else:
        # Show public competitions and private ones where user is a participant
        query = query.where(
            or_(
                Competition.visibility == Visibility.PUBLIC,
                Competition.id.in_(
                    select(Participant.competition_id).where(
                        Participant.user_id == current_user.id
                    )
                ),
            )
        )

    result = await db.execute(query)
    competitions = result.scalars().all()

    # Get participant counts
    response_list = []
    for comp in competitions:
        count_result = await db.execute(
            select(func.count(Participant.id)).where(
                Participant.competition_id == comp.id
            )
        )
        participant_count = count_result.scalar()

        # Check if user is participant
        participant_result = await db.execute(
            select(Participant).where(
                and_(
                    Participant.competition_id == comp.id,
                    Participant.user_id == current_user.id,
                )
            )
        )
        is_participant = participant_result.scalar_one_or_none() is not None

        comp_response = CompetitionListResponse(
            **{k: getattr(comp, k) for k in CompetitionListResponse.model_fields.keys() if k != 'participant_count' and k != 'user_is_participant'},
            participant_count=participant_count,
            user_is_participant=is_participant,
        )
        response_list.append(comp_response)

    return response_list


@router.get("/{competition_id}", response_model=CompetitionResponse)
async def get_competition(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific competition"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if user is participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    is_participant = participant_result.scalar_one_or_none() is not None

    # Get participant count
    count_result = await db.execute(
        select(func.count(Participant.id)).where(
            Participant.competition_id == competition.id
        )
    )
    participant_count = count_result.scalar()

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    response = CompetitionResponse.model_validate(competition)
    response.participant_count = participant_count
    response.user_is_participant = is_participant
    response.user_is_admin = is_admin

    return response


@router.patch("/{competition_id}", response_model=CompetitionResponse)
async def update_competition(
    competition_id: str,
    update_data: CompetitionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a competition (admins only)"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only competition admins can update competitions",
        )

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(competition, field, value)

    competition.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(competition)

    return CompetitionResponse.model_validate(competition)


@router.delete("/{competition_id}")
async def delete_competition(
    competition_id: str,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a competition (global admins only)"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    await db.delete(competition)
    await db.commit()

    return {"message": "Competition deleted successfully"}


@router.post("/{competition_id}/join", response_model=JoinRequestResponse)
async def join_competition(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a competition or request to join"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if already a participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a participant",
        )

    # Check if max participants reached
    if competition.max_participants:
        count_result = await db.execute(
            select(func.count(Participant.id)).where(
                Participant.competition_id == competition.id
            )
        )
        if count_result.scalar() >= competition.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competition is full",
            )

    # If open join, add participant directly
    if competition.join_type == "open":
        participant = Participant(
            user_id=current_user.id,
            competition_id=competition.id,
        )
        db.add(participant)
        await db.commit()

        return {"message": "Joined competition successfully"}

    # Otherwise, create join request
    join_request = JoinRequest(
        user_id=current_user.id,
        competition_id=competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db.add(join_request)
    await db.commit()
    await db.refresh(join_request)

    return JoinRequestResponse.model_validate(join_request)


@router.get("/{competition_id}/games")
async def get_competition_games(
    competition_id: str,
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD format)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get games for a competition, optionally filtered by date"""
    # Verify competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
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

    # Build query
    query = select(Game).where(Game.competition_id == competition_id)

    # Filter by date if provided
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(
                and_(
                    Game.scheduled_start_time >= start_of_day,
                    Game.scheduled_start_time <= end_of_day,
                )
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )

    # Execute query
    result = await db.execute(query.order_by(Game.scheduled_start_time))
    games = result.scalars().all()

    # Convert to response format with team details
    games_response = []
    for game in games:
        # Fetch home and away teams
        home_team_result = await db.execute(
            select(Team).where(Team.id == game.home_team_id)
        )
        home_team = home_team_result.scalar_one()

        away_team_result = await db.execute(
            select(Team).where(Team.id == game.away_team_id)
        )
        away_team = away_team_result.scalar_one()

        games_response.append({
            "id": str(game.id),
            "external_id": game.external_id,
            "scheduled_start_time": game.scheduled_start_time.isoformat(),
            "status": game.status.value,
            "home_team": {
                "id": str(home_team.id),
                "name": home_team.name,
                "city": home_team.city,
                "abbreviation": home_team.abbreviation,
            },
            "away_team": {
                "id": str(away_team.id),
                "name": away_team.name,
                "city": away_team.city,
                "abbreviation": away_team.abbreviation,
            },
            "home_team_score": game.home_team_score,
            "away_team_score": game.away_team_score,
            "venue_name": game.venue_name,
            "venue_city": game.venue_city,
        })

    return games_response


@router.get("/{competition_id}/available-selections")
async def get_available_selections(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available teams/golfers for fixed team selection"""
    # Verify competition exists
    comp_result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = comp_result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
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

    # Get league to determine sport type
    from app.models.league import League
    league_result = await db.execute(
        select(League).where(League.id == competition.league_id)
    )
    league = league_result.scalar_one()

    # Get already selected teams/golfers
    selected_result = await db.execute(
        select(FixedTeamSelection).where(
            FixedTeamSelection.competition_id == competition.id
        )
    )
    selected_selections = selected_result.scalars().all()
    selected_team_ids = {sel.team_id for sel in selected_selections if sel.team_id}
    selected_golfer_ids = {sel.golfer_id for sel in selected_selections if sel.golfer_id}

    # Build response based on sport type
    if league.sport == "PGA":
        # Get all golfers
        golfers_result = await db.execute(select(Golfer))
        golfers = golfers_result.scalars().all()

        return {
            "golfers": [
                {
                    "id": str(golfer.id),
                    "name": golfer.name,
                    "country": golfer.country,
                    "is_available": golfer.id not in selected_golfer_ids,
                }
                for golfer in golfers
            ]
        }
    else:
        # Get teams for this league
        teams_result = await db.execute(
            select(Team).where(Team.league_id == competition.league_id)
        )
        teams = teams_result.scalars().all()

        return {
            "teams": [
                {
                    "id": str(team.id),
                    "name": team.name,
                    "city": team.city,
                    "abbreviation": team.abbreviation,
                    "is_available": team.id not in selected_team_ids,
                }
                for team in teams
            ]
        }
