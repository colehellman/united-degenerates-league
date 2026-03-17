from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.competition_service as competition_service
import app.services.pick_service as pick_service
import app.services.user_service as user_service
from app.models.competition import Competition, CompetitionStatus
from app.models.game import Game, GameStatus
from app.models.league import Team
from app.models.participant import Participant
from app.models.pick import Pick
from app.models.user import AccountStatus, User
from app.services.score_service import score_picks_for_game


@pytest.mark.asyncio
async def test_score_picks_for_game(
    db_session: AsyncSession,
    active_competition: Competition,
    test_teams: list[Team],
    test_user: User,
):
    """Test scoring picks for a completed game."""
    game = Game(
        competition_id=active_competition.id,
        external_id="score_test",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=2),
        status=GameStatus.FINAL,
        home_team_score=24,
        away_team_score=17,
        winner_team_id=test_teams[0].id,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)

    # Participant record needed for stats recalculation
    participant = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(participant)
    await db_session.commit()

    await score_picks_for_game(db_session, game)
    await db_session.commit()
    await db_session.refresh(pick)
    await db_session.refresh(participant)

    assert pick.is_correct is True
    assert pick.points_earned == 1
    assert participant.total_points == 1
    assert participant.total_wins == 1


@pytest.mark.asyncio
async def test_update_competition_statuses(db_session: AsyncSession, test_league, test_user):
    """Test transitioning competitions between statuses."""
    now = datetime.utcnow()

    # Upcoming that should become active
    upcoming = Competition(
        name="Should be active",
        mode="daily_picks",
        league_id=test_league.id,
        start_date=now - timedelta(minutes=1),
        end_date=now + timedelta(days=1),
        status=CompetitionStatus.UPCOMING,
        creator_id=test_user.id,
    )

    # Active that should become completed
    active = Competition(
        name="Should be completed",
        mode="daily_picks",
        league_id=test_league.id,
        start_date=now - timedelta(days=2),
        end_date=now - timedelta(minutes=1),
        status=CompetitionStatus.ACTIVE,
        creator_id=test_user.id,
    )

    db_session.add_all([upcoming, active])
    await db_session.commit()

    await competition_service.update_competition_statuses(db_session)
    await db_session.commit()

    await db_session.refresh(upcoming)
    await db_session.refresh(active)

    assert upcoming.status == CompetitionStatus.ACTIVE
    assert active.status == CompetitionStatus.COMPLETED


@pytest.mark.asyncio
async def test_lock_expired_picks(
    db_session: AsyncSession,
    active_competition: Competition,
    test_teams: list[Team],
    test_user: User,
):
    """Test locking picks for games that have started."""
    game = Game(
        competition_id=active_competition.id,
        external_id="lock_test",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(minutes=5),
        status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game.id,
        predicted_winner_team_id=test_teams[0].id,
        is_locked=False,
    )
    db_session.add(pick)
    await db_session.commit()

    await pick_service.lock_expired_picks(db_session)
    await db_session.commit()
    await db_session.refresh(pick)

    assert pick.is_locked is True
    assert pick.locked_at is not None


@pytest.mark.asyncio
async def test_cleanup_pending_deletions(db_session: AsyncSession):
    """Test account deletion cleanup."""
    now = datetime.utcnow()
    user = User(
        email="delete_me@example.com",
        username="deleteme",
        hashed_password="...",
        status=AccountStatus.PENDING_DELETION,
        deletion_requested_at=now - timedelta(days=31),
    )
    db_session.add(user)
    await db_session.commit()

    await user_service.cleanup_pending_deletions(db_session)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.status == AccountStatus.DELETED
    assert user.email.startswith("deleted_user_")
    assert user.hashed_password == ""
