from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import async_session
from app.services.ws_manager import ScoreManager
from app.models.game import Game, GameStatus
from app.models.competition import Competition, CompetitionStatus
from app.models.league import Team
from app.services.sports_api.sports_service import sports_service
from app.services.score_service import score_picks_for_game
from app.services.sync_service import (
    _find_or_create_team,
    _apply_team_record,
    _sync_game_for_competition,
)
import app.services.competition_service as competition_service
import app.services.pick_service as pick_service
import app.services.user_service as user_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def update_game_scores():
    """
    Background job to update game scores from external APIs.
    """
    logger.info(f"Running score update job at {datetime.utcnow()}")

    async with async_session() as db:
        try:
            # Fetch games that need score updates
            stmt = (
                select(Game)
                .where(
                    Game.status.in_([GameStatus.SCHEDULED, GameStatus.IN_PROGRESS])
                )
                .options(
                    selectinload(Game.competition).selectinload(Competition.league),
                    selectinload(Game.home_team),
                    selectinload(Game.away_team),
                )
            )
            result = await db.execute(stmt)
            games = result.scalars().all()

            if not games:
                logger.debug("No active games to update")
                return

            games = sorted(games, key=lambda g: g.id)

            # Group games by league
            games_by_league = {}
            for game in games:
                league_name = game.competition.league.name
                if league_name not in games_by_league:
                    games_by_league[league_name] = []
                games_by_league[league_name].append(game)

            updated_games = []
            for league_name, league_games in games_by_league.items():
                try:
                    live_scores = await sports_service.get_live_scores(league_name)
                    scores_by_id = {score.external_id: score for score in live_scores}

                    for game in league_games:
                        score_data = scores_by_id.get(game.external_id)
                        if not score_data:
                            continue

                        was_not_final = game.status != GameStatus.FINAL
                        game.status = GameStatus(score_data.status)
                        game.home_team_score = score_data.home_score
                        game.away_team_score = score_data.away_score
                        
                        if score_data.spread is not None:
                            game.spread = score_data.spread
                        if score_data.over_under is not None:
                            game.over_under = score_data.over_under

                        if game.status == GameStatus.FINAL:
                            if score_data.home_score is not None and score_data.away_score is not None:
                                if score_data.home_score > score_data.away_score:
                                    game.winner_team_id = game.home_team_id
                                elif score_data.away_score > score_data.home_score:
                                    game.winner_team_id = game.away_team_id
                                else:
                                    game.winner_team_id = None
                            else:
                                game.winner_team_id = None
                        elif game.status in [GameStatus.CANCELLED, GameStatus.POSTPONED, GameStatus.NO_RESULT]:
                            game.winner_team_id = None

                        game.updated_at = datetime.utcnow()
                        updated_games.append(game)

                        if was_not_final and game.status == GameStatus.FINAL:
                            try:
                                await score_picks_for_game(db, game)
                            except Exception as score_err:
                                # Keep the game FINAL — the API data is correct.
                                # WARNING: scoring will NOT automatically retry because
                                # was_not_final will be False on subsequent cycles.
                                # Manual intervention or a dedicated recovery job is needed.
                                logger.critical(
                                    f"Pick scoring failed for game {game.id}. "
                                    f"Game stays FINAL but picks are UNSCORED. "
                                    f"MANUAL INTERVENTION REQUIRED. Error: {score_err}",
                                    exc_info=True,
                                )

                except Exception as e:
                    logger.error(f"Error updating scores for {league_name}: {str(e)}")
                    continue

            await db.commit()

            if updated_games:
                ws_payload = [
                    {
                        "game_id": str(g.id),
                        "status": g.status.value,
                        "home_score": g.home_team_score,
                        "away_score": g.away_team_score,
                        "home_team_id": str(g.home_team_id),
                        "away_team_id": str(g.away_team_id),
                        "winner_team_id": str(g.winner_team_id) if g.winner_team_id else None,
                    }
                    for g in updated_games
                ]
                await ScoreManager.publish_score_update(ws_payload)

            if updated_games and sports_service.redis_client:
                competition_ids = set(game.competition_id for game in updated_games)
                for comp_id in competition_ids:
                    cache_key = f"leaderboard:{comp_id}"
                    try:
                        sports_service.redis_client.delete(cache_key)
                    except Exception as e:
                        logger.error(f"Error invalidating cache: {e}")

        except Exception as e:
            logger.error(f"Error in update_game_scores: {str(e)}", exc_info=True)
            await db.rollback()


async def wrap_update_competition_statuses():
    async with async_session() as db:
        try:
            await competition_service.update_competition_statuses(db)
            await db.commit()
        except Exception as e:
            logger.error(f"Error in update_competition_statuses: {str(e)}", exc_info=True)
            await db.rollback()


async def wrap_lock_expired_picks():
    async with async_session() as db:
        try:
            await pick_service.lock_expired_picks(db)
            await db.commit()
        except Exception as e:
            logger.error(f"Error in lock_expired_picks: {str(e)}", exc_info=True)
            await db.rollback()


async def wrap_cleanup_pending_deletions():
    async with async_session() as db:
        try:
            await user_service.cleanup_pending_deletions(db)
            await db.commit()
        except Exception as e:
            logger.error(f"Error in cleanup_pending_deletions: {str(e)}", exc_info=True)
            await db.rollback()


async def sync_games_from_api():
    """
    Import today's games from ESPN into the database for active competitions.
    """
    logger.info(f"Running game sync job at {datetime.utcnow()}")

    async with async_session() as db:
        try:
            stmt = (
                select(Competition)
                .where(Competition.status.in_([CompetitionStatus.ACTIVE, CompetitionStatus.UPCOMING]))
                .options(selectinload(Competition.league))
            )
            result = await db.execute(stmt)
            competitions = result.scalars().all()

            if not competitions:
                return

            comps_by_league = {}
            for comp in competitions:
                league_name = comp.league.name
                league_key = league_name.value if hasattr(league_name, 'value') else str(league_name)
                if league_key not in comps_by_league:
                    comps_by_league[league_key] = {"league": comp.league, "competitions": []}
                comps_by_league[league_key]["competitions"].append(comp)

            total_created = 0
            total_updated = 0

            for league_key, data in comps_by_league.items():
                league = data["league"]
                league_comps = data["competitions"]

                try:
                    today_bg = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                    api_games = []
                    for days_ahead in range(3):
                        day = today_bg + timedelta(days=days_ahead)
                        day_games = await sports_service.get_schedule(league_key, day, day)
                        api_games.extend(day_games)

                    if not api_games:
                        continue

                    team_stmt = select(Team).where(Team.league_id == league.id)
                    team_result = await db.execute(team_stmt)
                    existing_teams = {t.external_id: t for t in team_result.scalars().all()}

                    for game_data in api_games:
                        home_team = await _find_or_create_team(
                            db, league.id, game_data.home_team,
                            game_data.home_team_external_id,
                            game_data.home_team_abbreviation,
                            existing_teams,
                        )
                        away_team = await _find_or_create_team(
                            db, league.id, game_data.away_team,
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

                        for comp in league_comps:
                            created, updated = await _sync_game_for_competition(
                                db, comp, game_data, home_team, away_team,
                            )
                            total_created += created
                            total_updated += updated

                except Exception as e:
                    logger.error(f"Error syncing games for {league_key}: {str(e)}")
                    continue

            await db.commit()
            logger.info(f"Game sync completed: {total_created} created, {total_updated} updated")

        except Exception as e:
            logger.error(f"Error in sync_games_from_api: {str(e)}", exc_info=True)
            await db.rollback()


def start_background_jobs():
    """Start all background jobs"""
    logger.info("Starting background jobs...")

    scheduler.add_job(
        update_game_scores,
        trigger=IntervalTrigger(seconds=settings.SCORE_UPDATE_INTERVAL_SECONDS),
        id="update_game_scores",
        replace_existing=True,
    )

    scheduler.add_job(
        wrap_update_competition_statuses,
        trigger=IntervalTrigger(minutes=5),
        id="update_competition_statuses",
        replace_existing=True,
    )

    scheduler.add_job(
        wrap_lock_expired_picks,
        trigger=IntervalTrigger(seconds=60),
        id="lock_expired_picks",
        replace_existing=True,
    )

    scheduler.add_job(
        sync_games_from_api,
        trigger=IntervalTrigger(minutes=5),
        id="sync_games_from_api",
        replace_existing=True,
    )

    scheduler.add_job(
        wrap_cleanup_pending_deletions,
        trigger="cron",
        hour=2,
        minute=0,
        id="cleanup_pending_deletions",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background jobs started successfully")


def stop_background_jobs():
    """Stop all background jobs"""
    logger.info("Stopping background jobs...")
    scheduler.shutdown()
    logger.info("Background jobs stopped")
