import logging
from datetime import datetime
from sqlalchemy import select, and_, update
from app.models.game import Game, GameStatus
from app.models.pick import Pick

logger = logging.getLogger(__name__)

async def lock_expired_picks(db):
    """
    Background job to lock picks for games that have started.
    """
    logger.info(f"Running pick locking job at {datetime.utcnow()}")
    now = datetime.utcnow()

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
                Pick.is_locked.is_(False)
            )
        )
        .values(
            is_locked=True,
            locked_at=now
        )
    )
    result = await db.execute(stmt)
    locked_count = result.rowcount

    logger.info(f"Locked {locked_count} picks for {len(started_games)} games")
