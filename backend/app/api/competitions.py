from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.deps import get_db, get_current_user, get_current_global_admin
from app.models.user import User
from app.models.competition import Competition, CompetitionStatus, Visibility
from app.models.user import UserRole
from app.models.participant import Participant, JoinRequest, JoinRequestStatus
from app.models.game import Game
from app.models.league import Team, Golfer, League
from app.models.pick import FixedTeamSelection
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionResponse,
    CompetitionUpdate,
    CompetitionListResponse,
)
from app.schemas.participant import JoinRequestCreate, JoinRequestResponse

router = APIRouter()


# Month (1-12) each league's season normally begins.
# Leagues whose season spans two calendar years (NBA Oct→Jun, NHL Oct→Jun,
# NFL Sep→Feb, EPL Aug→May) must use this map so H2H lookups don't miss
# October-December games when the calendar year rolls over to January.
_LEAGUE_SEASON_START_MONTH: dict = {
    "NFL": 9,            # September
    "NCAA_FOOTBALL": 9,  # September
    "NBA": 10,           # October
    "NHL": 10,           # October
    "NCAA_BASKETBALL": 11,  # November
    "EPL": 8,            # August
    "UCL": 8,            # August (Union of European Football Leagues, v2)
    "MLS": 3,            # March
    "MLB": 4,            # April  (single calendar year — Jan anchor works too)
    "PGA": 9,            # PGA Tour season runs Sep-Aug
}


def _season_start(league_name: str) -> datetime:
    """Return the start-of-day datetime for the beginning of the current season.

    For cross-year leagues (NBA, NHL, NFL …) the season might have started in a
    prior calendar year.  E.g. on 2026-03-10, NBA season started 2025-10-01.
    """
    now = datetime.utcnow()
    start_month = _LEAGUE_SEASON_START_MONTH.get(league_name, 1)
    # If we haven't yet reached the start month this calendar year, the season
    # began in the previous calendar year.
    season_year = now.year if now.month >= start_month else now.year - 1
    return datetime(season_year, start_month, 1)


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

    # Set initial status based on start_date.
    # If start_date is now or in the past the competition is immediately ACTIVE;
    # otherwise it waits for the scheduled status-update job.
    now = datetime.utcnow()
    initial_status = (
        CompetitionStatus.ACTIVE
        if competition_data.start_date <= now
        else CompetitionStatus.UPCOMING
    )

    # Create competition
    competition = Competition(
        **competition_data.model_dump(),
        creator_id=current_user.id,
        league_admin_ids=[current_user.id],  # Creator is default admin
        status=initial_status,
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

    # Sync games for this specific competition immediately so the creator sees
    # today's games right away without waiting for the 5-minute scheduled job.
    # Previously used BackgroundTasks (unreliable on Render free tier) and called
    # sync_games_from_api which syncs ALL competitions — both were wrong.
    # We fire-and-forget with a bare except so a transient ESPN outage never
    # prevents the 201 from reaching the client.
    try:
        from app.services.sync_service import sync_games_for_competition
        await sync_games_for_competition(db, str(competition.id))
    except Exception:
        pass  # Non-critical; the scheduled job and admin sync button are fallbacks

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

    # Subquery for participant counts
    participant_counts_subquery = (
        select(
            Participant.competition_id,
            func.count(Participant.id).label("participant_count")
        )
        .group_by(Participant.competition_id)
        .subquery()
    )

    # Subquery to check if the current user is a participant
    user_participant_subquery = (
        select(Participant.competition_id)
        .where(Participant.user_id == current_user.id)
        .subquery()
    )

    # Main query joining with subqueries
    query = (
        select(
            Competition,
            func.coalesce(participant_counts_subquery.c.participant_count, 0).label("participant_count"),
            user_participant_subquery.c.competition_id.is_not(None).label("is_participant")
        )
        .outerjoin(
            participant_counts_subquery,
            Competition.id == participant_counts_subquery.c.competition_id
        )
        .outerjoin(
            user_participant_subquery,
            Competition.id == user_participant_subquery.c.competition_id
        )
    )

    # Filter by status if provided
    if status_filter:
        query = query.where(Competition.status == status_filter)

    # Filter by visibility
    if visibility:
        query = query.where(Competition.visibility == visibility)
    else:
        # Show public competitions and private ones where user is a participant OR creator
        query = query.where(
            or_(
                Competition.visibility == Visibility.PUBLIC,
                user_participant_subquery.c.competition_id.is_not(None),
                Competition.creator_id == current_user.id
            )
        )

    result = await db.execute(query)
    rows = result.all()

    response_list = []
    for comp, participant_count, is_participant in rows:
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
        current_user.id in competition.league_admin_ids
        or current_user.role == UserRole.GLOBAL_ADMIN
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
        current_user.id in competition.league_admin_ids
        or current_user.role == UserRole.GLOBAL_ADMIN
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


@router.post("/{competition_id}/join")
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
    utc_offset_minutes: Optional[int] = Query(
        0,
        description=(
            "Client timezone offset in minutes west of UTC "
            "(JavaScript's Date.getTimezoneOffset()). "
            "Games are stored as naive UTC; this converts the local date "
            "window to the equivalent UTC range so a 7pm ET game appears "
            "on the correct local date rather than the next UTC day."
        ),
    ),
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

    # Filter by date if provided, adjusting for the client's local timezone.
    # Games are stored as naive UTC. The client sends utc_offset_minutes
    # (JS Date.getTimezoneOffset()) so we can convert "local midnight–midnight"
    # to the correct UTC range.
    #
    # JS getTimezoneOffset() convention: UTC = local + offset.
    # So UTC-5 (Eastern Standard) returns +300, UTC+1 returns -60, etc.
    # To find UTC midnight from local midnight: utc = local + timedelta(minutes=offset).
    #
    # E.g. UTC-5 (EST) offset=300:
    #   local 2026-03-08 00:00 → UTC 2026-03-08 05:00
    #   local 2026-03-08 23:59 → UTC 2026-03-09 04:59
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            offset = timedelta(minutes=utc_offset_minutes or 0)
            start_of_day = date_obj + offset
            end_of_day = start_of_day + timedelta(hours=24) - timedelta(microseconds=1)
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

    # Resolve the competition's league name once so _season_start() can pick
    # the correct cross-year anchor for H2H queries (NBA, NHL, NFL etc. all
    # have seasons that begin mid-year in the prior calendar year).
    league_result = await db.execute(
        select(League).where(League.id == competition.league_id)
    )
    league = league_result.scalar_one_or_none()
    league_name = league.name.value if league else "unknown"
    h2h_season_start = _season_start(league_name)

    # Pre-fetch all teams for this competition's games in one query to avoid
    # N+1 selects in the loop below.
    team_ids = set()
    for game in games:
        team_ids.add(game.home_team_id)
        team_ids.add(game.away_team_id)

    teams_by_id: dict = {}
    if team_ids:
        team_result = await db.execute(
            select(Team).where(Team.id.in_(list(team_ids)))
        )
        for t in team_result.scalars().all():
            teams_by_id[t.id] = t

    # Pre-fetch H2H games for all team pairs in one query to avoid N+1.
    # We fetch all finished games this season that involve any of the teams
    # playing in today's games.
    h2h_games_all = []
    if team_ids:
        h2h_all_result = await db.execute(
            select(Game).where(
                and_(
                    Game.winner_team_id.is_not(None),
                    Game.scheduled_start_time >= h2h_season_start,
                    Game.home_team_id.in_(list(team_ids)),
                    Game.away_team_id.in_(list(team_ids))
                )
            )
        )
        h2h_games_all = h2h_all_result.scalars().all()

    # Convert to response format with team details
    games_response = []
    for game in games:
        home_team = teams_by_id.get(game.home_team_id)
        away_team = teams_by_id.get(game.away_team_id)

        if not home_team or not away_team:
            continue

        # Filter pre-fetched H2H games for this specific pair
        h2h_games = [
            g for g in h2h_games_all
            if (g.home_team_id == home_team.id and g.away_team_id == away_team.id) or
               (g.home_team_id == away_team.id and g.away_team_id == home_team.id)
        ]
        
        h2h_home_wins = sum(1 for g in h2h_games if g.winner_team_id == home_team.id)
        h2h_away_wins = sum(1 for g in h2h_games if g.winner_team_id == away_team.id)

        def _record_str(wins, losses, ties):
            """Format W-L or W-L-T, returning None if no data."""
            if wins is None and losses is None:
                return None
            w = wins or 0
            l = losses or 0
            if ties:
                return f"{w}-{l}-{ties}"
            return f"{w}-{l}"

        games_response.append({
            "id": str(game.id),
            "external_id": game.external_id,
            # Append "Z" so the frontend knows this is UTC. The column is a naive
            # DateTime but game.py confirms values are always stored as UTC.
            # Without the suffix, JavaScript treats the string as local time and
            # displays it 5 hours early for Eastern-timezone users.
            "scheduled_start_time": game.scheduled_start_time.isoformat() + "Z",
            "status": game.status.value,
            "home_team": {
                "id": str(home_team.id),
                "name": home_team.name,
                "city": home_team.city,
                "abbreviation": home_team.abbreviation,
                # Season record synced from ESPN each cycle; None until first sync.
                "record": _record_str(home_team.wins, home_team.losses, home_team.ties),
                # Head-to-head wins against the opponent this season.
                "h2h_wins": h2h_home_wins,
            },
            "away_team": {
                "id": str(away_team.id),
                "name": away_team.name,
                "city": away_team.city,
                "abbreviation": away_team.abbreviation,
                "record": _record_str(away_team.wins, away_team.losses, away_team.ties),
                "h2h_wins": h2h_away_wins,
            },
            "home_team_score": game.home_team_score,
            "away_team_score": game.away_team_score,
            "venue_name": game.venue_name,
            "venue_city": game.venue_city,
            "spread": game.spread,
        })

    return games_response


@router.post("/{competition_id}/sync-games")
async def sync_competition_games(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force an immediate ESPN game sync for a specific competition.

    Accessible to competition admins and global admins. Runs synchronously
    so the caller sees errors and game counts immediately rather than relying
    on the silent 5-minute background job.
    """
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")

    # Compare UUID objects directly — league_admin_ids is ARRAY(UUID(as_uuid=True))
    # so asyncpg returns Python uuid.UUID instances, not strings.
    is_admin = (
        current_user.id in competition.league_admin_ids
        or current_user.role == UserRole.GLOBAL_ADMIN
    )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Competition admin access required",
        )

    from app.services.sync_service import sync_games_for_competition

    try:
        sync_result = await sync_games_for_competition(db, competition_id)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ESPN sync failed: {str(exc)}",
        )

    return sync_result


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
