"""
Critical Path Tests for United Degenerates League

These tests cover the most important user flows:
1. User registration and login
2. Competition joining
3. Pick submission and locking
4. Game scoring
5. Leaderboard calculation

Run with: pytest tests/test_critical_paths.py -v
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, AccountStatus
from app.models.competition import Competition, CompetitionMode, CompetitionStatus, Visibility, JoinType
from app.models.league import League, LeagueName, Team
from app.models.game import Game, GameStatus
from app.models.participant import Participant
from app.models.pick import Pick
from app.core.security import get_password_hash
from tests.conftest import _login

# ── Authentication Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    """Test user registration endpoint — returns TokenResponse"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securePassword123",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["username"] == "newuser"


@pytest.mark.asyncio
async def test_user_login(client: AsyncClient, test_user: User):
    """Test user login endpoint — accepts JSON UserLogin"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "Password123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user: User):
    """Test login with invalid credentials"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword",
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pending_deletion_user_cannot_login(client: AsyncClient, db_session: AsyncSession):
    """PENDING_DELETION users are blocked at login, not at the API dependency level.

    Design: deps.get_current_user only hard-blocks DELETED accounts. PENDING_DELETION
    users retain API access with their existing token during the 30-day grace period
    so they can cancel. Login (auth.py) blocks PENDING_DELETION from issuing NEW tokens,
    bounding the window to the token TTL (30 minutes).
    """
    pending = User(
        email="pending@example.com",
        username="pendinguser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.PENDING_DELETION,
    )
    db_session.add(pending)
    await db_session.commit()

    # Login must be rejected — PENDING_DELETION cannot obtain new tokens
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "pending@example.com", "password": "Password123"},
    )
    assert login_resp.status_code == 403
    assert "not active" in login_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_via_cookie(client: AsyncClient, test_user: User):
    """Refresh token must work via httpOnly cookie (no Authorization header).

    The client fixture sends cookies automatically because it uses
    follow_redirects and the auth router sets the refresh_token cookie.
    """
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "Password123"},
    )
    assert login_resp.status_code == 200
    # refresh_token cookie is set by the backend
    assert "refresh_token" in login_resp.cookies

    # Call refresh without Authorization header — cookie is sent automatically
    refresh_resp = await client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data


# ── Competition Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_competitions(client: AsyncClient, test_user: User, active_competition: Competition):
    """Test listing competitions"""
    token = await _login(client)

    response = await client.get(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "Active Comp"


@pytest.mark.asyncio
async def test_join_competition(client: AsyncClient, test_user: User, active_competition: Competition, db_session: AsyncSession):
    """Test joining a competition"""
    token = await _login(client)

    response = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [200, 201]

    # Verify participant was created
    result = await db_session.execute(
        select(Participant).where(
            Participant.user_id == test_user.id,
            Participant.competition_id == active_competition.id,
        )
    )
    participant = result.scalar_one_or_none()
    assert participant is not None


# ── Pick Submission Tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_daily_pick(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_game: Game,
    test_teams: list[Team],
    db_session: AsyncSession
):
    """Test submitting a daily pick"""
    # Create participant first
    participant = Participant(
        user_id=test_user.id,
        competition_id=active_competition.id,
    )
    db_session.add(participant)
    await db_session.commit()

    token = await _login(client)

    response = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "picks": [
                {
                    "game_id": str(test_game.id),
                    "predicted_winner_team_id": str(test_teams[0].id),
                }
            ]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["game_id"] == str(test_game.id)
    assert data[0]["predicted_winner_team_id"] == str(test_teams[0].id)
    assert data[0]["is_locked"] is False


@pytest.mark.asyncio
async def test_cannot_submit_pick_after_game_starts(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list[Team],
    db_session: AsyncSession
):
    """Test that picks cannot be submitted after game starts"""
    # Create participant
    participant = Participant(
        user_id=test_user.id,
        competition_id=active_competition.id,
    )
    db_session.add(participant)

    # Create game that already started
    game = Game(
        competition_id=active_competition.id,
        external_id="test_game_started",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=1),  # 1 hour ago
        status=GameStatus.IN_PROGRESS,
        venue_name="Test Stadium",
        venue_city="Test City",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    response = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "picks": [
                {
                    "game_id": str(game.id),
                    "predicted_winner_team_id": str(test_teams[0].id),
                }
            ]
        }
    )
    assert response.status_code == 400
    assert "already started" in response.json()["detail"].lower()


# ── Pick Locking Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pick_locking(db_session: AsyncSession, test_user: User, active_competition: Competition, test_teams: list[Team]):
    """Test that picks are locked when game starts"""
    # Create participant
    participant = Participant(
        user_id=test_user.id,
        competition_id=active_competition.id,
    )
    db_session.add(participant)

    # Create game whose start time is in the past so lock_expired_picks will lock it
    game = Game(
        competition_id=active_competition.id,
        external_id="test_game_locking",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(minutes=1),
        status=GameStatus.SCHEDULED,
        venue_name="Test Stadium",
        venue_city="Test City",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    # Create pick
    pick = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game.id,
        predicted_winner_team_id=test_teams[0].id,
    )
    db_session.add(pick)
    await db_session.commit()
    await db_session.refresh(pick)

    # Initially not locked
    assert pick.is_locked is False

    # Simulate background job locking picks
    from app.services.background_jobs import lock_expired_picks
    await lock_expired_picks()

    # Refresh pick — it must be locked since the game start time has passed
    await db_session.refresh(pick)
    assert pick.is_locked is True


# ── Game Scoring Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pick_scoring(db_session: AsyncSession, test_user: User, active_competition: Competition, test_teams: list[Team]):
    """Test that picks are scored correctly when game finishes"""
    # Create participant
    participant = Participant(
        user_id=test_user.id,
        competition_id=active_competition.id,
    )
    db_session.add(participant)

    # Create finished game
    game = Game(
        competition_id=active_competition.id,
        external_id="test_game_finished",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
        home_team_score=28,
        away_team_score=21,
        winner_team_id=test_teams[0].id,  # Home team won
        venue_name="Test Stadium",
        venue_city="Test City",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    # Create correct pick
    pick_correct = Pick(
        user_id=test_user.id,
        competition_id=active_competition.id,
        game_id=game.id,
        predicted_winner_team_id=test_teams[0].id,  # Picked home team (winner)
        is_locked=True,
        locked_at=datetime.utcnow() - timedelta(hours=3),
    )
    db_session.add(pick_correct)
    await db_session.commit()
    await db_session.refresh(pick_correct)

    # Simulate background job scoring picks
    from app.services.background_jobs import _score_picks_for_game
    await _score_picks_for_game(db_session, game)

    # Refresh pick
    await db_session.refresh(pick_correct)

    # Should be marked as correct with 1 point
    assert pick_correct.is_correct is True
    assert pick_correct.points_earned == 1

    # Participant stats must also be updated
    await db_session.refresh(participant)
    assert participant.total_wins == 1
    assert participant.total_losses == 0
    assert participant.total_points == 1
    assert participant.accuracy_percentage == 100.0


# ── Leaderboard Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leaderboard_calculation(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession
):
    """Test leaderboard calculation"""
    # Create participant with some stats (use actual Participant model fields)
    participant = Participant(
        user_id=test_user.id,
        competition_id=active_competition.id,
        total_points=10,
        total_wins=8,
        total_losses=2,
        accuracy_percentage=80.0,
    )
    db_session.add(participant)
    await db_session.commit()

    token = await _login(client)

    response = await client.get(
        f"/api/leaderboards/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # Verify participant is in leaderboard (LeaderboardEntry schema fields)
    user_entry = next((entry for entry in data if entry["user_id"] == str(test_user.id)), None)
    assert user_entry is not None
    assert user_entry["total_points"] == 10
    assert user_entry["total_wins"] == 8
    assert user_entry["rank"] == 1  # Should be rank 1 since only participant


# ── Competition Status Transition Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_competition_status_transition(db_session: AsyncSession, test_user: User, test_league: League):
    """Test that competitions transition from UPCOMING to ACTIVE"""
    # Create upcoming competition that should become active
    competition = Competition(
        name="Upcoming Competition",
        description="Test",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.UPCOMING,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(seconds=5),  # Just started
        end_date=datetime.utcnow() + timedelta(days=7),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(competition)
    await db_session.commit()
    await db_session.refresh(competition)

    # Initially UPCOMING
    assert competition.status == CompetitionStatus.UPCOMING

    # Simulate background job updating statuses
    from app.services.background_jobs import update_competition_statuses
    await update_competition_statuses()

    # Refresh competition
    await db_session.refresh(competition)

    # Should now be ACTIVE
    assert competition.status == CompetitionStatus.ACTIVE


# ── Competition Creation Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_create_competition(client: AsyncClient, test_user: User, test_league: League):
    """Test creating a competition via POST /api/competitions.

    This exercises the full request path: Pydantic validation → model_dump()
    unpacking → SQLAlchemy insert → response serialization. It catches
    type errors (e.g. str vs UUID) and schema mismatches that ORM-only
    fixtures miss.
    """
    token = await _login(client)

    response = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Daily Picks",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "visibility": "public",
            "join_type": "open",
        }
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["name"] == "Test Daily Picks"
    assert data["mode"] == "daily_picks"
    assert data["status"] == "upcoming"
    assert data["participant_count"] == 1  # Creator auto-joined
    assert data["user_is_participant"] is True
    assert data["user_is_admin"] is True


@pytest.mark.asyncio
async def test_create_competition_with_all_options(client: AsyncClient, test_user: User, test_league: League):
    """Test creating a competition with every optional field set."""
    token = await _login(client)

    response = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Full Options Comp",
            "description": "Testing all fields",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "display_timezone": "America/New_York",
            "visibility": "private",
            "join_type": "requires_approval",
            "max_participants": 20,
            "max_picks_per_day": 10,
        }
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["max_participants"] == 20
    assert data["max_picks_per_day"] == 10
    assert data["visibility"] == "private"
    assert data["join_type"] == "requires_approval"


@pytest.mark.asyncio
async def test_create_competition_tz_aware_dates(client: AsyncClient, test_user: User, test_league: League):
    """Test that ISO dates with 'Z' suffix (tz-aware) don't crash asyncpg.

    Browsers send '2026-03-10T00:00:00.000Z' but the DB uses
    TIMESTAMP WITHOUT TIME ZONE.  The schema must strip tzinfo so asyncpg
    doesn't choke mixing tz-aware and naive datetimes in the same INSERT.
    """
    token = await _login(client)

    response = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "TZ Aware Dates Test",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": "2026-03-10T00:00:00Z",
            "end_date": "2026-03-17T00:00:00Z",
            "visibility": "public",
            "join_type": "open",
        }
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_create_competition_invalid_dates(client: AsyncClient, test_user: User, test_league: League):
    """Test that end_date before start_date is rejected."""
    token = await _login(client)

    response = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Bad Dates",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "visibility": "public",
            "join_type": "open",
        }
    )
    assert response.status_code == 400


# ── Account Deletion Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_pending_deletions(db_session: AsyncSession):
    """cleanup_pending_deletions must anonymize users past the 30-day grace period
    and leave users still within the grace period untouched.
    """
    now = datetime.utcnow()

    # User past grace period — should be anonymized
    old_user = User(
        email="old@example.com",
        username="olduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.PENDING_DELETION,
        deletion_requested_at=now - timedelta(days=31),
    )
    # User still within grace period — must NOT be touched
    recent_user = User(
        email="recent@example.com",
        username="recentuser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.PENDING_DELETION,
        deletion_requested_at=now - timedelta(days=5),
    )
    db_session.add_all([old_user, recent_user])
    await db_session.commit()
    await db_session.refresh(old_user)
    await db_session.refresh(recent_user)

    from app.services.background_jobs import cleanup_pending_deletions
    await cleanup_pending_deletions()

    await db_session.refresh(old_user)
    await db_session.refresh(recent_user)

    # Old user must be anonymized
    assert old_user.status == AccountStatus.DELETED
    assert old_user.hashed_password == ""
    assert "deleted" in old_user.email

    # Recent user must be untouched
    assert recent_user.status == AccountStatus.PENDING_DELETION
    assert recent_user.email == "recent@example.com"


if __name__ == "__main__":
    # Run tests with: python -m pytest backend/tests/test_critical_paths.py -v
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
