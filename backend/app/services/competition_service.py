import logging
from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.orm import selectinload

from app.models.competition import Competition, CompetitionStatus
from app.models.game import GameStatus
from app.models.pick import FixedTeamSelection

logger = logging.getLogger(__name__)


async def update_competition_statuses(db):
    """
    Background job to update competition statuses.
    """
    logger.info(f"Running competition status update job at {datetime.utcnow()}")
    now = datetime.utcnow()

    # Transition UPCOMING -> ACTIVE
    stmt = select(Competition).where(
        and_(Competition.status == CompetitionStatus.UPCOMING, Competition.start_date <= now)
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
        .where(and_(Competition.status == CompetitionStatus.ACTIVE, Competition.end_date <= now))
        .options(selectinload(Competition.games))
    )
    result = await db.execute(stmt)
    active_comps = result.scalars().all()

    for comp in active_comps:
        # Check if all games are finished
        all_finished = all(
            game.status
            in [GameStatus.FINAL, GameStatus.CANCELLED, GameStatus.POSTPONED, GameStatus.NO_RESULT]
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


async def _lock_fixed_team_selections(db, competition_id):
    """Lock all fixed team selections for a competition that just started."""
    now = datetime.utcnow()

    stmt = (
        update(FixedTeamSelection)
        .where(
            and_(
                FixedTeamSelection.competition_id == competition_id,
                FixedTeamSelection.is_locked.is_(False),
            )
        )
        .values(is_locked=True, locked_at=now)
    )
    result = await db.execute(stmt)
    locked_count = result.rowcount

    logger.info(f"Locked {locked_count} fixed team selections for competition {competition_id}")
