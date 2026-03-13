import logging
from sqlalchemy import select, and_, update
from app.models.game import Game
from app.models.pick import Pick
from app.models.participant import Participant

logger = logging.getLogger(__name__)

async def score_picks_for_game(db, game: Game):
    """
    Score all picks for a completed game.
    """
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
            # Tie, cancelled, or no result: award no points
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
    participant_keys = set((pick.user_id, pick.competition_id) for pick in picks)

    for user_id, competition_id in participant_keys:
        await recalculate_participant_stats(db, user_id, competition_id)

async def recalculate_participant_stats(db, user_id, competition_id):
    """
    Recalculate aggregate stats for a participant.
    """
    # Fetch all scored picks for this participant
    stmt = (
        select(Pick)
        .where(
            and_(
                Pick.user_id == user_id,
                Pick.competition_id == competition_id,
                Pick.is_correct.isnot(None)
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
