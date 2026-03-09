import pytest
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.background_jobs import (
    _recalculate_participant_stats,
    _score_picks_for_game,
    _find_or_create_team,
    _sync_game_for_competition,
    _lock_fixed_team_selections,
    lock_expired_picks,
    cleanup_pending_deletions,
    update_competition_statuses,
    update_game_scores,
    sync_games_from_api,
    sync_games_for_competition,
    start_background_jobs,
    stop_background_jobs,
)
from app.models.user import User, AccountStatus
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.models.pick import Pick, FixedTeamSelection
from app.models.game import Game, GameStatus
from app.models.league import Team


def _make_session_patcher(db_session: AsyncSession):
    """Return a callable that acts like async_session() context manager, yielding the test session."""
    @asynccontextmanager
    async def _fake_ctx():
        yield db_session

    class _FakeMaker:
        def __call__(self):
            return _fake_ctx()

    return _FakeMaker()


@pytest.mark.asyncio
async def test_recalculate_participant_stats(
    db_session: AsyncSession, test_user: User, active_competition: Competition,
    test_teams: list,
):
    """Test that participant stats are correctly recalculated."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    # Create two games (unique constraint ix_picks_user_comp_game requires distinct game_ids)
    game_a = Game(
        competition_id=active_competition.id,
        external_id="recalc_game_a",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=1),
        status=GameStatus.FINAL,
    )
    game_b = Game(
        competition_id=active_competition.id,
        external_id="recalc_game_b",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.FINAL,
    )
    db_session.add_all([game_a, game_b])
    await db_session.commit()
    await db_session.refresh(game_a)
    await db_session.refresh(game_b)

    # Create one winning and one losing pick
    pick1 = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game_a.id,
        predicted_winner_team_id=test_teams[0].id,
        is_correct=True,
        points_earned=1,
    )
    pick2 = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game_b.id,
        predicted_winner_team_id=test_teams[1].id,
        is_correct=False,
        points_earned=0,
    )
    db_session.add_all([pick1, pick2])
    await db_session.commit()

    await _recalculate_participant_stats(db_session, test_user.id, active_competition.id)

    await db_session.refresh(p)
    assert p.total_points == 1
    assert p.total_wins == 1
    assert p.total_losses == 1
    assert p.accuracy_percentage == 50.0


@pytest.mark.asyncio
async def test_recalculate_participant_stats_no_picks(
    db_session: AsyncSession, test_user: User, active_competition: Competition
):
    """Participant with no picks gets zero stats."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    await _recalculate_participant_stats(db_session, test_user.id, active_competition.id)

    await db_session.refresh(p)
    assert p.total_points == 0
    assert p.accuracy_percentage == 0.0


@pytest.mark.asyncio
async def test_score_picks_for_game_correct_pick(
    db_session: AsyncSession, test_user: User, active_competition: Competition,
    test_game: Game, test_teams: list,
):
    """Picks for the winning team are scored as correct (1 point)."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)

    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=test_game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)
    await db_session.commit()

    test_game.winner_team_id = test_teams[0].id
    await db_session.commit()

    await _score_picks_for_game(db_session, test_game)
    await db_session.commit()
    await db_session.refresh(pick)

    assert pick.is_correct is True
    assert pick.points_earned == 1


@pytest.mark.asyncio
async def test_score_picks_for_game_incorrect_pick(
    db_session: AsyncSession, test_user: User, active_competition: Competition,
    test_game: Game, test_teams: list,
):
    """Picks for the losing team are scored as incorrect (0 points)."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)

    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=test_game.id,
        predicted_winner_team_id=test_teams[1].id,
    )
    db_session.add(pick)
    await db_session.commit()

    test_game.winner_team_id = test_teams[0].id
    await db_session.commit()

    await _score_picks_for_game(db_session, test_game)
    await db_session.commit()
    await db_session.refresh(pick)

    assert pick.is_correct is False
    assert pick.points_earned == 0


@pytest.mark.asyncio
async def test_score_picks_for_game_tie(
    db_session: AsyncSession, test_user: User, active_competition: Competition,
    test_game: Game, test_teams: list,
):
    """When game has no winner (tie), all picks get 0 points."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)

    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=test_game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)
    await db_session.commit()

    test_game.winner_team_id = None
    await db_session.commit()

    await _score_picks_for_game(db_session, test_game)
    await db_session.commit()
    await db_session.refresh(pick)

    # Void games leave is_correct=None so they don't count as losses.
    # Only points_earned is zeroed out.
    assert pick.is_correct is None
    assert pick.points_earned == 0


@pytest.mark.asyncio
async def test_score_picks_for_game_no_picks(
    db_session: AsyncSession, active_competition: Competition, test_game: Game
):
    """_score_picks_for_game handles a game with no picks gracefully."""
    test_game.winner_team_id = None
    await db_session.commit()
    await _score_picks_for_game(db_session, test_game)  # should not raise


@pytest.mark.asyncio
async def test_find_or_create_team_new(db_session: AsyncSession, test_league):
    """_find_or_create_team creates a new Team when not in cache."""
    cache = {}
    team = await _find_or_create_team(
        db_session, test_league.id, "New Team", "ext_new", "NWT", cache
    )
    await db_session.commit()

    assert team is not None
    assert team.name == "New Team"
    assert "ext_new" in cache


@pytest.mark.asyncio
async def test_find_or_create_team_from_cache(
    db_session: AsyncSession, test_league, test_teams: list
):
    """_find_or_create_team returns cached team without a DB insert."""
    cache = {"team_a": test_teams[0]}
    result = await _find_or_create_team(
        db_session, test_league.id, "Team A", "team_a", "TA", cache
    )
    assert result is test_teams[0]


@pytest.mark.asyncio
async def test_find_or_create_team_no_external_id_returns_none(
    db_session: AsyncSession, test_league
):
    """_find_or_create_team returns None when external_id is falsy."""
    result = await _find_or_create_team(db_session, test_league.id, "Team", None, "T", {})
    assert result is None


@pytest.mark.asyncio
async def test_sync_game_create(
    db_session: AsyncSession, active_competition: Competition, test_teams: list
):
    """_sync_game_for_competition creates a new game when it does not exist."""
    from app.services.sports_api.base import GameData

    game_data = GameData(
        external_id="brand_new_game",
        home_team="Home",
        away_team="Away",
        scheduled_start_time=datetime.utcnow() + timedelta(hours=3),
        status="scheduled",
    )
    created, updated = await _sync_game_for_competition(
        db_session, active_competition, game_data, test_teams[0], test_teams[1]
    )
    await db_session.commit()

    assert created == 1
    assert updated == 0


@pytest.mark.asyncio
async def test_sync_game_update(
    db_session: AsyncSession, active_competition: Competition,
    test_game: Game, test_teams: list,
):
    """_sync_game_for_competition updates an existing game's score."""
    from app.services.sports_api.base import GameData

    game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=test_game.scheduled_start_time,
        status="in_progress",
        home_score=7,
        away_score=3,
    )
    created, updated = await _sync_game_for_competition(
        db_session, active_competition, game_data, test_teams[0], test_teams[1]
    )
    await db_session.commit()

    assert created == 0
    assert updated == 1


@pytest.mark.asyncio
async def test_sync_game_becomes_final_scores_picks(
    db_session: AsyncSession, test_user: User, active_competition: Competition,
    test_game: Game, test_teams: list,
):
    """When a synced game becomes FINAL, picks are automatically scored."""
    from app.services.sports_api.base import GameData

    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=test_game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)
    # Game starts as SCHEDULED
    test_game.status = GameStatus.SCHEDULED
    await db_session.commit()

    game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=test_game.scheduled_start_time,
        status="final",
        home_score=21,
        away_score=14,
    )
    await _sync_game_for_competition(
        db_session, active_competition, game_data, test_teams[0], test_teams[1]
    )
    await db_session.commit()
    await db_session.refresh(pick)

    # Pick should be scored (correct since home team won and pick was home team)
    assert pick.is_correct is True


@pytest.mark.asyncio
async def test_lock_fixed_team_selections_direct(
    db_session: AsyncSession, test_user: User, upcoming_fixed_comp: Competition, test_teams: list
):
    """_lock_fixed_team_selections sets is_locked=True on all unlocked selections."""
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    db_session.add(p)
    selection = FixedTeamSelection(
        user_id=test_user.id,
        competition_id=upcoming_fixed_comp.id,
        team_id=test_teams[0].id,
        is_locked=False,
    )
    db_session.add(selection)
    await db_session.commit()
    await db_session.refresh(selection)

    await _lock_fixed_team_selections(db_session, upcoming_fixed_comp.id)
    await db_session.commit()
    await db_session.refresh(selection)

    assert selection.is_locked is True
    assert selection.locked_at is not None


@pytest.mark.asyncio
async def test_lock_expired_picks_via_job(
    db_session: AsyncSession, test_user: User, active_competition: Competition, test_teams: list
):
    """lock_expired_picks job locks picks for games that have started."""
    started_game = Game(
        competition_id=active_competition.id,
        external_id="started_g",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(minutes=5),
        status=GameStatus.IN_PROGRESS,
    )
    db_session.add(started_game)
    await db_session.commit()
    await db_session.refresh(started_game)

    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=started_game.id,
        predicted_winner_team_id=test_teams[0].id,
        is_locked=False,
    )
    db_session.add(pick)
    await db_session.commit()
    await db_session.refresh(pick)

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await lock_expired_picks()

    await db_session.refresh(pick)
    assert pick.is_locked is True


@pytest.mark.asyncio
async def test_cleanup_pending_deletions_via_job(
    db_session: AsyncSession, test_user: User
):
    """cleanup_pending_deletions anonymizes users past the 30-day grace period."""
    test_user.status = AccountStatus.PENDING_DELETION
    test_user.deletion_requested_at = datetime.utcnow() - timedelta(days=31)
    await db_session.commit()

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await cleanup_pending_deletions()

    await db_session.refresh(test_user)
    assert test_user.status == AccountStatus.DELETED
    assert "deleted_user" in test_user.email


@pytest.mark.asyncio
async def test_cleanup_pending_deletions_no_users(db_session: AsyncSession):
    """cleanup_pending_deletions is a no-op when no users qualify."""
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await cleanup_pending_deletions()  # should not raise


@pytest.mark.asyncio
async def test_update_competition_statuses_upcoming_to_active(
    db_session: AsyncSession, test_league, test_user: User
):
    """Competitions past start_date transition from UPCOMING to ACTIVE."""
    from app.models.competition import Competition, CompetitionMode, Visibility, JoinType

    comp = Competition(
        name="Soon Active",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.UPCOMING,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(minutes=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await update_competition_statuses()

    await db_session.refresh(comp)
    assert comp.status == CompetitionStatus.ACTIVE


@pytest.mark.asyncio
async def test_update_game_scores_no_active_games(db_session: AsyncSession):
    """update_game_scores does nothing when there are no SCHEDULED/IN_PROGRESS games."""
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await update_game_scores()  # should not raise


@pytest.mark.asyncio
async def test_update_game_scores_updates_in_progress_game(
    db_session: AsyncSession, test_user: User, active_competition, test_game: Game, test_teams: list
):
    """update_game_scores updates scores for in-progress games from the API."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    # Set game to in_progress
    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    mock_game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=test_game.scheduled_start_time,
        status="in_progress",
        home_score=14,
        away_score=7,
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[mock_game_data]),
        ):
            with patch("app.services.background_jobs.ScoreManager.publish_score_update", new=AsyncMock()):
                await update_game_scores()

    await db_session.refresh(test_game)
    assert test_game.home_team_score == 14
    assert test_game.away_team_score == 7


@pytest.mark.asyncio
async def test_update_game_scores_scores_picks_on_final(
    db_session: AsyncSession, test_user: User, active_competition, test_game: Game, test_teams: list
):
    """update_game_scores scores picks when a game transitions to FINAL."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=test_game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)
    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    mock_game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=test_game.scheduled_start_time,
        status="final",
        home_score=21,
        away_score=14,
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[mock_game_data]),
        ):
            with patch("app.services.background_jobs.ScoreManager.publish_score_update", new=AsyncMock()):
                with patch("app.services.background_jobs.sports_service.redis_client", None):
                    await update_game_scores()

    await db_session.refresh(pick)
    assert pick.is_correct is True


@pytest.mark.asyncio
async def test_sync_games_from_api_no_active_competitions(db_session: AsyncSession):
    """sync_games_from_api does nothing when there are no active competitions."""
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await sync_games_from_api()  # should not raise


@pytest.mark.asyncio
async def test_sync_games_from_api_creates_games(
    db_session: AsyncSession, test_user: User, active_competition, test_league
):
    """sync_games_from_api creates new games from ESPN data."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    mock_game_data = GameData(
        external_id="espn_new_game",
        home_team="Team A",
        away_team="Team B",
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status="scheduled",
        home_team_external_id="ext_a",
        away_team_external_id="ext_b",
        home_team_abbreviation="TA",
        away_team_abbreviation="TB",
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            # sync_games_from_api now calls get_schedule (today + 2 days)
            "app.services.background_jobs.sports_service.get_schedule",
            new=AsyncMock(return_value=[mock_game_data]),
        ):
            await sync_games_from_api()

    # Verify a game was created
    stmt = select(Game).where(Game.competition_id == active_competition.id)
    result = await db_session.execute(stmt)
    games = result.scalars().all()
    assert any(g.external_id == "espn_new_game" for g in games)


@pytest.mark.asyncio
async def test_update_competition_statuses_active_to_completed(
    db_session: AsyncSession, test_league, test_user: User, test_teams: list
):
    """Active competition with all games FINAL transitions to COMPLETED."""
    from app.models.competition import Competition, CompetitionMode, Visibility, JoinType

    comp = Competition(
        name="Finishing Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow() - timedelta(minutes=1),  # already ended
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    # Add a FINAL game so all_finished is True
    game = Game(
        competition_id=comp.id,
        external_id="finished_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
    )
    db_session.add(game)
    await db_session.commit()

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await update_competition_statuses()

    await db_session.refresh(comp)
    assert comp.status == CompetitionStatus.COMPLETED


@pytest.mark.asyncio
async def test_update_game_scores_tie_game(
    db_session: AsyncSession, test_user: User, active_competition, test_game: Game, test_teams: list
):
    """update_game_scores handles tie (no winner) correctly."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    score_data = GameData(
        external_id=test_game.external_id,
        home_team="Team A",
        away_team="Team B",
        scheduled_start_time=datetime.utcnow(),
        status="final",
        home_score=14,
        away_score=14,  # Tie!
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[score_data]),
        ):
            with patch("app.services.background_jobs.ScoreManager.publish_score_update", new=AsyncMock()):
                await update_game_scores()

    await db_session.refresh(test_game)
    assert test_game.status == GameStatus.FINAL
    assert test_game.winner_team_id is None  # tie → no winner


@pytest.mark.asyncio
async def test_lock_expired_picks_no_started_games(db_session: AsyncSession):
    """lock_expired_picks exits early when no games have started."""
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await lock_expired_picks()  # should not raise (no started games → early return)


@pytest.mark.asyncio
async def test_update_competition_statuses_games_still_in_progress(
    db_session: AsyncSession, test_league, test_user: User, test_teams: list
):
    """Active comp past end_date but with in-progress games stays ACTIVE (debug branch)."""
    from app.models.competition import Competition, CompetitionMode, Visibility, JoinType

    comp = Competition(
        name="Slow Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow() - timedelta(minutes=1),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    # Game still IN_PROGRESS → all_finished is False → stays ACTIVE
    game = Game(
        competition_id=comp.id,
        external_id="still_going",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.IN_PROGRESS,
    )
    db_session.add(game)
    await db_session.commit()

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        await update_competition_statuses()

    await db_session.refresh(comp)
    assert comp.status == CompetitionStatus.ACTIVE  # not completed yet


@pytest.mark.asyncio
async def test_sync_games_from_api_no_api_games_for_league(
    db_session: AsyncSession, test_user: User, active_competition
):
    """sync_games_from_api logs and continues when API returns no games for a league."""
    from unittest.mock import AsyncMock

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[]),  # empty → continue
        ):
            await sync_games_from_api()  # should not raise


@pytest.mark.asyncio
async def test_update_game_scores_away_team_wins(
    db_session: AsyncSession, test_user: User, active_competition, test_game: Game, test_teams: list
):
    """update_game_scores sets away_team as winner when away_score > home_score."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    score_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=datetime.utcnow(),
        status="final",
        home_score=7,
        away_score=21,  # away wins
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[score_data]),
        ):
            with patch("app.services.background_jobs.ScoreManager.publish_score_update", new=AsyncMock()):
                await update_game_scores()

    await db_session.refresh(test_game)
    assert test_game.status == GameStatus.FINAL
    assert test_game.winner_team_id == test_game.away_team_id  # away wins


@pytest.mark.asyncio
async def test_update_game_scores_game_not_in_api_response(
    db_session: AsyncSession, test_user: User, active_competition, test_game: Game, test_teams: list
):
    """update_game_scores skips games not returned by the API (continue branch)."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    # Return a game with a different external_id → test_game not in scores_by_id
    different_game = GameData(
        external_id="completely_different_id",
        home_team="Home",
        away_team="Away",
        scheduled_start_time=datetime.utcnow(),
        status="in_progress",
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        with patch(
            "app.services.background_jobs.sports_service.get_live_scores",
            new=AsyncMock(return_value=[different_game]),
        ):
            with patch("app.services.background_jobs.ScoreManager.publish_score_update", new=AsyncMock()):
                await update_game_scores()

    await db_session.refresh(test_game)
    assert test_game.status == GameStatus.IN_PROGRESS  # unchanged


@pytest.mark.asyncio
async def test_sync_game_for_competition_away_wins(
    db_session: AsyncSession, active_competition, test_teams: list, test_game: Game
):
    """_sync_game_for_competition sets away team as winner when away_score > home_score."""
    from app.services.sports_api.base import GameData

    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=datetime.utcnow(),
        status="final",
        home_score=7,
        away_score=14,  # away wins
    )

    _, updated = await _sync_game_for_competition(
        db_session, active_competition, game_data, test_teams[0], test_teams[1]
    )

    await db_session.refresh(test_game)
    assert updated == 1
    assert test_game.winner_team_id == test_teams[1].id  # away team wins


@pytest.mark.asyncio
async def test_sync_game_for_competition_tie(
    db_session: AsyncSession, active_competition, test_teams: list, test_game: Game
):
    """_sync_game_for_competition sets winner_team_id=None for ties."""
    from app.services.sports_api.base import GameData

    test_game.status = GameStatus.IN_PROGRESS
    await db_session.commit()

    game_data = GameData(
        external_id=test_game.external_id,
        home_team="Home",
        away_team="Away",
        scheduled_start_time=datetime.utcnow(),
        status="final",
        home_score=14,
        away_score=14,  # tie
    )

    await _sync_game_for_competition(
        db_session, active_competition, game_data, test_teams[0], test_teams[1]
    )

    await db_session.refresh(test_game)
    assert test_game.winner_team_id is None  # tie


def _make_failing_session(error=None):
    """Return a session factory whose session.execute always raises."""
    from unittest.mock import AsyncMock, MagicMock

    exc = error or Exception("DB error")

    class _FailingSession:
        async def execute(self, *a, **kw):
            raise exc
        async def rollback(self):
            pass

    @asynccontextmanager
    async def _ctx():
        yield _FailingSession()

    class _Maker:
        def __call__(self):
            return _ctx()

    return _Maker()


@pytest.mark.asyncio
async def test_lock_expired_picks_db_error():
    """lock_expired_picks handles DB errors gracefully without raising."""
    with patch("app.services.background_jobs.async_session", _make_failing_session()):
        await lock_expired_picks()  # should not raise


@pytest.mark.asyncio
async def test_cleanup_pending_deletions_db_error():
    """cleanup_pending_deletions handles DB errors gracefully without raising."""
    with patch("app.services.background_jobs.async_session", _make_failing_session()):
        await cleanup_pending_deletions()  # should not raise


@pytest.mark.asyncio
async def test_update_competition_statuses_db_error():
    """update_competition_statuses handles DB errors gracefully without raising."""
    with patch("app.services.background_jobs.async_session", _make_failing_session()):
        await update_competition_statuses()  # should not raise


@pytest.mark.asyncio
async def test_sync_games_from_api_outer_exception():
    """sync_games_from_api handles unexpected outer DB errors gracefully."""
    with patch("app.services.background_jobs.async_session", _make_failing_session()):
        await sync_games_from_api()  # should not raise


def test_start_and_stop_background_jobs():
    """start_background_jobs and stop_background_jobs should not raise."""
    start_background_jobs()
    stop_background_jobs()


# ---------------------------------------------------------------------------
# sync_games_for_competition
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_games_for_competition_not_found(db_session: AsyncSession):
    """Returns a 'not found' message for a non-existent competition id."""
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher):
        result = await sync_games_for_competition("00000000-0000-0000-0000-000000000000")

    assert result["created"] == 0
    assert result["updated"] == 0
    assert "message" in result


@pytest.mark.asyncio
async def test_sync_games_for_competition_no_games_from_espn(
    db_session: AsyncSession,
    active_competition: Competition,
):
    """Returns a 'no games' message when ESPN returns an empty scoreboard."""
    from unittest.mock import AsyncMock
    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher), \
         patch(
             # sync_games_for_competition loops get_schedule per date now
             "app.services.background_jobs.sports_service.get_schedule",
             new=AsyncMock(return_value=[]),
         ):
        result = await sync_games_for_competition(str(active_competition.id))

    assert result["created"] == 0
    assert result["updated"] == 0
    assert "message" in result


@pytest.mark.asyncio
async def test_sync_games_for_competition_creates_games(
    db_session: AsyncSession,
    active_competition: Competition,
    test_teams: list,
):
    """sync_games_for_competition creates new games when ESPN returns data."""
    from app.services.sports_api.base import GameData
    from unittest.mock import AsyncMock

    mock_game = GameData(
        external_id="sgfc_game_001",
        home_team=test_teams[0].name,
        away_team=test_teams[1].name,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=3),
        status="scheduled",
        home_team_external_id=test_teams[0].external_id,
        away_team_external_id=test_teams[1].external_id,
        home_team_abbreviation=test_teams[0].abbreviation,
        away_team_abbreviation=test_teams[1].abbreviation,
    )

    session_patcher = _make_session_patcher(db_session)
    with patch("app.services.background_jobs.async_session", session_patcher), \
         patch(
             # sync_games_for_competition now loops get_schedule per date
             "app.services.background_jobs.sports_service.get_schedule",
             new=AsyncMock(return_value=[mock_game]),
         ):
        result = await sync_games_for_competition(str(active_competition.id))

    assert result["created"] >= 1
    # Verify a game landed in the DB for this competition
    stmt = select(Game).where(
        Game.competition_id == active_competition.id,
        Game.external_id == "sgfc_game_001",
    )
    db_result = await db_session.execute(stmt)
    assert db_result.scalar_one_or_none() is not None
