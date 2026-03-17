import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select

from app.models.competition import Competition
from app.models.game import Game, GameStatus
from app.models.league import Team
from app.services.sports_api.base import GameData
from app.services.sports_api.sports_service import sports_service

logger = logging.getLogger(__name__)


async def _find_or_create_team(
    db,
    league_id,
    name: str,
    external_id: str,
    abbreviation: str,
    cache: dict,
) -> Team | None:
    """Find existing team by external_id or create a new one."""
    if not external_id:
        return None

    # Check in-memory cache first
    if external_id in cache:
        return cache[external_id]

    # Create new team
    team = Team(
        league_id=league_id,
        name=name,
        external_id=external_id,
        abbreviation=abbreviation or name[:3].upper(),
    )
    db.add(team)
    await db.flush()  # get the ID

    cache[external_id] = team
    logger.info(f"Created team: {name} ({abbreviation})")
    return team


def _apply_team_record(
    team: Team,
    wins: int | None,
    losses: int | None,
    ties: int | None,
) -> None:
    """Update a Team's season record in-place when the API provides values."""
    if wins is not None:
        team.wins = wins
    if losses is not None:
        team.losses = losses
    if ties is not None:
        team.ties = ties


async def _sync_game_for_competition(
    db,
    competition: Competition,
    game_data: GameData,
    home_team: Team,
    away_team: Team,
) -> tuple[int, int]:
    """Sync a single game for a competition. Returns (created_count, updated_count)."""
    # Check if game already exists for this competition
    stmt = select(Game).where(
        and_(
            Game.competition_id == competition.id,
            Game.external_id == game_data.external_id,
        )
    )
    result = await db.execute(stmt)
    existing_game = result.scalar_one_or_none()

    if existing_game:
        # Update scores and status
        from app.services.score_service import score_picks_for_game

        was_not_final = existing_game.status != GameStatus.FINAL
        new_status = GameStatus(game_data.status)

        existing_game.status = new_status
        existing_game.home_team_score = game_data.home_score
        existing_game.away_team_score = game_data.away_score

        # Always update odds (spread/over_under) if available
        if game_data.spread is not None:
            existing_game.spread = game_data.spread
        if game_data.over_under is not None:
            existing_game.over_under = game_data.over_under

        existing_game.updated_at = datetime.utcnow()

        # Determine winner correctly
        if (
            new_status == GameStatus.FINAL
            and game_data.home_score is not None
            and game_data.away_score is not None
        ):
            if game_data.home_score > game_data.away_score:
                existing_game.winner_team_id = home_team.id
            elif game_data.away_score > game_data.home_score:
                existing_game.winner_team_id = away_team.id
            else:
                existing_game.winner_team_id = None  # Tie

        # Score picks when game just completed.
        if was_not_final and new_status == GameStatus.FINAL:
            try:
                await score_picks_for_game(db, existing_game)
            except Exception as score_err:
                logger.critical(
                    f"Pick scoring failed for game {existing_game.id} after marking FINAL. "
                    f"Reverting to IN_PROGRESS to allow retry. Error: {score_err}",
                    exc_info=True,
                )
                existing_game.status = GameStatus.IN_PROGRESS
                existing_game.winner_team_id = None

        return (0, 1)
    # Create new game.
    start_time = game_data.scheduled_start_time
    if start_time is not None and start_time.tzinfo is not None:
        start_time = start_time.astimezone(UTC).replace(tzinfo=None)

    game = Game(
        competition_id=competition.id,
        external_id=game_data.external_id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        scheduled_start_time=start_time,
        status=GameStatus(game_data.status),
        home_team_score=game_data.home_score,
        away_team_score=game_data.away_score,
        venue_name=game_data.venue,
        spread=game_data.spread,
        over_under=game_data.over_under,
    )
    db.add(game)
    return (1, 0)


async def sync_games_for_competition(db, competition_id: str) -> dict:
    """Sync games from ESPN for a single competition."""
    from sqlalchemy.orm import selectinload

    # Load competition with its league
    stmt = (
        select(Competition)
        .where(Competition.id == competition_id)
        .options(selectinload(Competition.league))
    )
    result = await db.execute(stmt)
    competition = result.scalar_one_or_none()

    if not competition:
        return {"created": 0, "updated": 0, "message": "Competition not found"}

    league = competition.league
    league_key = league.name.value if hasattr(league.name, "value") else str(league.name)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    comp_end = competition.end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    fetch_through = min(comp_end, today + timedelta(days=14))

    api_games: list = []
    current = today
    while current <= fetch_through:
        day_games = await sports_service.get_schedule(league_key, current, current)
        api_games.extend(day_games)
        current += timedelta(days=1)

    if not api_games:
        return {
            "created": 0,
            "updated": 0,
            "message": f"No games returned by ESPN for {league_key} in competition window",
        }

    # Build team cache: external_id -> Team
    team_stmt = select(Team).where(Team.league_id == league.id)
    team_result = await db.execute(team_stmt)
    existing_teams = {t.external_id: t for t in team_result.scalars().all()}

    total_created = 0
    total_updated = 0

    for game_data in api_games:
        home_team = await _find_or_create_team(
            db,
            league.id,
            game_data.home_team,
            game_data.home_team_external_id,
            game_data.home_team_abbreviation,
            existing_teams,
        )
        away_team = await _find_or_create_team(
            db,
            league.id,
            game_data.away_team,
            game_data.away_team_external_id,
            game_data.away_team_abbreviation,
            existing_teams,
        )

        if not home_team or not away_team:
            continue

        _apply_team_record(
            home_team,
            game_data.home_team_wins,
            game_data.home_team_losses,
            game_data.home_team_ties,
        )
        _apply_team_record(
            away_team,
            game_data.away_team_wins,
            game_data.away_team_losses,
            game_data.away_team_ties,
        )

        created, updated = await _sync_game_for_competition(
            db,
            competition,
            game_data,
            home_team,
            away_team,
        )
        total_created += created
        total_updated += updated

    logger.info(
        f"sync_games_for_competition({competition_id}): "
        f"{total_created} created, {total_updated} updated"
    )
    return {"created": total_created, "updated": total_updated}
