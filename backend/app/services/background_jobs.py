from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
from typing import List
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import async_session
from app.models.game import Game, GameStatus
from app.models.pick import Pick, FixedTeamSelection
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.models.user import User, AccountStatus
from app.services.sports_api.sports_service import sports_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _score_picks_for_game(db, game: Game):
    """
    Score all picks for a completed game.

    Rules per spec:
    - If game has a winner: correct picks get 1 point
    - If game is tie/cancelled/no result: all picks get 0 points
    """
    from app.models.pick import Pick

    # Fetch all picks for this game
    stmt = select(Pick).where(Pick.game_id == game.id)
    result = await db.execute(stmt)
    picks = result.scalars().all()

    if not picks:
        logger.debug(f"No picks found for game {game.id}")
        return

    scored_count = 0
    for pick in picks:
        # Determine if pick is correct
        if game.winner_team_id is None:
            # Tie, cancelled, or no result - no points awarded
            pick.is_correct = False
            pick.points_earned = 0
        elif pick.predicted_winner_team_id == game.winner_team_id:
            # Correct pick
            pick.is_correct = True
            pick.points_earned = 1
        else:
            # Incorrect pick
            pick.is_correct = False
            pick.points_earned = 0

        scored_count += 1

    logger.info(f"Scored {scored_count} picks for game {game.id}")

    # Recalculate participant aggregate stats
    # Get unique (user_id, competition_id) pairs from picks
    participant_keys = set((pick.user_id, pick.competition_id) for pick in picks)

    for user_id, competition_id in participant_keys:
        await _recalculate_participant_stats(db, user_id, competition_id)


async def _recalculate_participant_stats(db, user_id, competition_id):
    """
    Recalculate aggregate stats for a participant.

    Aggregates:
    - total_points: sum of all points_earned from picks
    - total_wins: count of correct picks
    - total_losses: count of incorrect picks
    - accuracy_percentage: wins / (wins + losses) * 100
    """
    # Fetch all scored picks for this participant
    stmt = (
        select(Pick)
        .where(
            and_(
                Pick.user_id == user_id,
                Pick.competition_id == competition_id,
                Pick.is_correct.isnot(None)  # Only count scored picks
            )
        )
    )
    result = await db.execute(stmt)
    picks = result.scalars().all()

    total_points = sum(pick.points_earned for pick in picks)
    total_wins = sum(1 for pick in picks if pick.is_correct is True)
    total_losses = sum(1 for pick in picks if pick.is_correct is False)

    total_picks = total_wins + total_losses
    accuracy = (total_wins / total_picks * 100.0) if total_picks > 0 else 0.0

    # Update participant record
    stmt = (
        update(Participant)
        .where(
            and_(
                Participant.user_id == user_id,
                Participant.competition_id == competition_id
            )
        )
        .values(
            total_points=total_points,
            total_wins=total_wins,
            total_losses=total_losses,
            accuracy_percentage=accuracy,
        )
    )
    await db.execute(stmt)

    logger.debug(
        f"Updated participant stats: user={user_id}, comp={competition_id}, "
        f"points={total_points}, wins={total_wins}, losses={total_losses}"
    )


async def update_game_scores():
    """
    Background job to update game scores from external APIs.
    Runs every 60 seconds during active games.

    Process:
    1. Fetch active/in-progress games from database
    2. Group by league and call external sports APIs
    3. Update game records with latest scores and status
    4. Score all picks for completed games
    5. Recalculate participant aggregate stats
    6. Invalidate leaderboard cache
    """
    logger.info(f"Running score update job at {datetime.utcnow()}")

    async with async_session() as db:
        try:
            # Fetch games that need score updates (scheduled or in_progress)
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

            logger.info(f"Found {len(games)} games to update")

            # Group games by league for efficient API calls
            games_by_league = {}
            for game in games:
                league_name = game.competition.league.name
                if league_name not in games_by_league:
                    games_by_league[league_name] = []
                games_by_league[league_name].append(game)

            # Update scores for each league
            updated_games = []
            for league_name, league_games in games_by_league.items():
                try:
                    # Fetch live scores from API
                    live_scores = await sports_service.get_live_scores(league_name)

                    # Create lookup by external_id
                    scores_by_id = {score.external_id: score for score in live_scores}

                    # Update each game
                    for game in league_games:
                        score_data = scores_by_id.get(game.external_id)
                        if not score_data:
                            continue

                        # Track if game just became final
                        was_not_final = game.status != GameStatus.FINAL

                        # Update game data
                        game.status = GameStatus(score_data.status)
                        game.home_team_score = score_data.home_score
                        game.away_team_score = score_data.away_score

                        # Determine winner (NULL for ties, cancelled, or no result)
                        if game.status == GameStatus.FINAL:
                            if score_data.home_score is not None and score_data.away_score is not None:
                                if score_data.home_score > score_data.away_score:
                                    game.winner_team_id = game.home_team_id
                                elif score_data.away_score > score_data.home_score:
                                    game.winner_team_id = game.away_team_id
                                else:
                                    # Tie - no winner
                                    game.winner_team_id = None
                            else:
                                # Missing scores - no winner
                                game.winner_team_id = None
                        elif game.status in [GameStatus.CANCELLED, GameStatus.POSTPONED, GameStatus.NO_RESULT]:
                            # No winner for cancelled/postponed games
                            game.winner_team_id = None

                        game.updated_at = datetime.utcnow()
                        updated_games.append(game)

                        # Score picks if game just became final
                        if was_not_final and game.status == GameStatus.FINAL:
                            await _score_picks_for_game(db, game)

                    logger.info(f"Updated {len(league_games)} games for {league_name}")

                except Exception as e:
                    logger.error(f"Error updating scores for {league_name}: {str(e)}")
                    continue

            # Commit all updates
            await db.commit()
            logger.info(f"Score update completed: {len(updated_games)} games updated")

            # Invalidate relevant caches (if Redis available)
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


async def update_competition_statuses():
    """
    Background job to update competition statuses.
    Runs every 5 minutes.

    Process:
    1. Check for UPCOMING competitions that should transition to ACTIVE
       (start_date has passed)
    2. Check for ACTIVE competitions that should transition to COMPLETED
       (end_date has passed AND all games are finished)
    3. Lock fixed team selections when competition starts
    4. Freeze standings when competition completes (no action needed - just status change)
    """
    logger.info(f"Running competition status update job at {datetime.utcnow()}")
    now = datetime.utcnow()

    async with async_session() as db:
        try:
            # Transition UPCOMING -> ACTIVE
            stmt = (
                select(Competition)
                .where(
                    and_(
                        Competition.status == CompetitionStatus.UPCOMING,
                        Competition.start_date <= now
                    )
                )
            )
            result = await db.execute(stmt)
            upcoming_comps = result.scalars().all()

            for comp in upcoming_comps:
                comp.status = CompetitionStatus.ACTIVE
                comp.updated_at = now
                logger.info(f"Competition {comp.id} ({comp.name}) transitioned to ACTIVE")

                # Lock fixed team selections for this competition
                await _lock_fixed_team_selections(db, comp.id)

            # Transition ACTIVE -> COMPLETED
            stmt = (
                select(Competition)
                .where(
                    and_(
                        Competition.status == CompetitionStatus.ACTIVE,
                        Competition.end_date <= now
                    )
                )
                .options(selectinload(Competition.games))
            )
            result = await db.execute(stmt)
            active_comps = result.scalars().all()

            for comp in active_comps:
                # Check if all games are finished
                all_finished = all(
                    game.status in [GameStatus.FINAL, GameStatus.CANCELLED, GameStatus.POSTPONED, GameStatus.NO_RESULT]
                    for game in comp.games
                )

                if all_finished:
                    comp.status = CompetitionStatus.COMPLETED
                    comp.updated_at = now
                    logger.info(f"Competition {comp.id} ({comp.name}) transitioned to COMPLETED")
                else:
                    logger.debug(
                        f"Competition {comp.id} ({comp.name}) end date passed but games still in progress"
                    )

            await db.commit()
            logger.info("Competition status update completed")

        except Exception as e:
            logger.error(f"Error in update_competition_statuses: {str(e)}", exc_info=True)
            await db.rollback()


async def _lock_fixed_team_selections(db, competition_id):
    """Lock all fixed team selections for a competition that just started."""
    now = datetime.utcnow()

    stmt = (
        update(FixedTeamSelection)
        .where(
            and_(
                FixedTeamSelection.competition_id == competition_id,
                FixedTeamSelection.is_locked == False
            )
        )
        .values(
            is_locked=True,
            locked_at=now
        )
    )
    result = await db.execute(stmt)
    locked_count = result.rowcount

    logger.info(f"Locked {locked_count} fixed team selections for competition {competition_id}")


async def lock_expired_picks():
    """
    Background job to lock picks for games that have started.
    Runs every 60 seconds.

    Process:
    1. Find games that have started (scheduled_start_time <= now)
    2. Lock all unlocked picks for those games
    3. Set locked_at timestamp

    Note: Picks lock at exact game start time per spec (UTC-based)
    """
    logger.info(f"Running pick locking job at {datetime.utcnow()}")
    now = datetime.utcnow()

    async with async_session() as db:
        try:
            # Find games that have started but have unlocked picks
            stmt = (
                select(Game)
                .where(
                    and_(
                        Game.scheduled_start_time <= now,
                        Game.status.in_([GameStatus.SCHEDULED, GameStatus.IN_PROGRESS])
                    )
                )
            )
            result = await db.execute(stmt)
            started_games = result.scalars().all()

            if not started_games:
                logger.debug("No games to lock picks for")
                return

            game_ids = [game.id for game in started_games]

            # Lock all unlocked picks for these games
            stmt = (
                update(Pick)
                .where(
                    and_(
                        Pick.game_id.in_(game_ids),
                        Pick.is_locked == False
                    )
                )
                .values(
                    is_locked=True,
                    locked_at=now
                )
            )
            result = await db.execute(stmt)
            locked_count = result.rowcount

            await db.commit()
            logger.info(f"Locked {locked_count} picks for {len(started_games)} games")

        except Exception as e:
            logger.error(f"Error in lock_expired_picks: {str(e)}", exc_info=True)
            await db.rollback()


async def cleanup_pending_deletions():
    """
    Background job to permanently delete accounts after 30-day grace period.
    Runs once per day at 2 AM UTC.

    Process per spec section 13.1:
    1. Find users with status=PENDING_DELETION and deletion_requested_at > 30 days ago
    2. Anonymize their historical data (picks remain for league integrity)
    3. Delete user account
    """
    logger.info(f"Running account deletion cleanup job at {datetime.utcnow()}")
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    async with async_session() as db:
        try:
            # Find users pending deletion past grace period
            stmt = (
                select(User)
                .where(
                    and_(
                        User.status == AccountStatus.PENDING_DELETION,
                        User.deletion_requested_at <= cutoff
                    )
                )
            )
            result = await db.execute(stmt)
            users_to_delete = result.scalars().all()

            if not users_to_delete:
                logger.info("No pending deletions to process")
                return

            logger.info(f"Found {len(users_to_delete)} accounts to delete")

            for user in users_to_delete:
                # Anonymize user data
                user.email = f"deleted_user_{user.id}@deleted.local"
                user.username = f"Deleted User #{user.id}"
                user.hashed_password = ""
                user.status = AccountStatus.DELETED
                user.updated_at = now

                # Historical picks and participants remain in database for integrity
                # but are now associated with anonymized user

                logger.info(f"Deleted and anonymized user {user.id}")

            await db.commit()
            logger.info(f"Account deletion cleanup completed: {len(users_to_delete)} users deleted")

        except Exception as e:
            logger.error(f"Error in cleanup_pending_deletions: {str(e)}", exc_info=True)
            await db.rollback()


def start_background_jobs():
    """Start all background jobs"""
    logger.info("Starting background jobs...")

    # Score updates (every 60 seconds)
    scheduler.add_job(
        update_game_scores,
        trigger=IntervalTrigger(seconds=settings.SCORE_UPDATE_INTERVAL_SECONDS),
        id="update_game_scores",
        name="Update game scores from APIs",
        replace_existing=True,
    )

    # Competition status updates (every 5 minutes)
    scheduler.add_job(
        update_competition_statuses,
        trigger=IntervalTrigger(minutes=5),
        id="update_competition_statuses",
        name="Update competition lifecycle statuses",
        replace_existing=True,
    )

    # Lock expired picks (every 60 seconds)
    scheduler.add_job(
        lock_expired_picks,
        trigger=IntervalTrigger(seconds=60),
        id="lock_expired_picks",
        name="Lock picks for started games",
        replace_existing=True,
    )

    # Cleanup pending deletions (daily at 2 AM UTC)
    scheduler.add_job(
        cleanup_pending_deletions,
        trigger="cron",
        hour=2,
        minute=0,
        id="cleanup_pending_deletions",
        name="Cleanup pending account deletions",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background jobs started successfully")


def stop_background_jobs():
    """Stop all background jobs"""
    logger.info("Stopping background jobs...")
    scheduler.shutdown()
    logger.info("Background jobs stopped")
