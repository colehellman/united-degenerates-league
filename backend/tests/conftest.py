import asyncio
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import async_session, engine
from app.main import app
from app.models.competition import (
    Competition,
    CompetitionMode,
    CompetitionStatus,
    JoinType,
    Visibility,
)
from app.models.game import Game, GameStatus
from app.models.invite_link import InviteLink
from app.models.league import League, LeagueName, Team
from app.models.participant import Participant
from app.models.user import AccountStatus, User, UserRole


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop — all async tests share one loop.

    This prevents asyncpg InterfaceError caused by pooled connections
    being accessed from a different event loop than the one they were
    created on.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """Provide a database session with per-test table cleanup.

    Before each test, all tables are truncated so tests are fully isolated.
    """
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE picks, fixed_team_selections, join_requests, "
                "invite_links, participants, games, competitions, golfers, teams, "
                "leagues, audit_logs, bug_reports, users CASCADE"
            )
        )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client():
    """Async HTTP test client wired to the FastAPI ASGI app.

    Uses ASGITransport which does NOT invoke the app lifespan,
    so background jobs and Redis subscribers are not started.
    """

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def second_user(db_session: AsyncSession):
    user = User(
        email="second@example.com",
        username="seconduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_league(db_session: AsyncSession):
    league = League(
        name=LeagueName.NFL,
        display_name="National Football League",
        is_team_based=True,
    )
    db_session.add(league)
    await db_session.commit()
    await db_session.refresh(league)
    return league


@pytest.fixture
async def test_league_2(db_session: AsyncSession):
    league = League(
        name=LeagueName.NBA,
        display_name="National Basketball Association",
        is_team_based=True,
    )
    db_session.add(league)
    await db_session.commit()
    await db_session.refresh(league)
    return league


@pytest.fixture
async def test_teams(db_session: AsyncSession, test_league: League):
    teams = [
        Team(
            league_id=test_league.id,
            name="Team A",
            city="City A",
            abbreviation="TA",
            external_id="team_a",
        ),
        Team(
            league_id=test_league.id,
            name="Team B",
            city="City B",
            abbreviation="TB",
            external_id="team_b",
        ),
    ]
    db_session.add_all(teams)
    await db_session.commit()
    for t in teams:
        await db_session.refresh(t)
    return teams


@pytest.fixture
async def active_competition(db_session: AsyncSession, test_league: League, test_user: User):
    """Active competition where test_user is creator + admin."""
    comp = Competition(
        name="Active Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        max_picks_per_day=10,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp


@pytest.fixture
async def approval_competition(db_session: AsyncSession, test_league: League, test_user: User):
    """Competition that requires approval to join."""
    comp = Competition(
        name="Approval Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.REQUIRES_APPROVAL,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp


@pytest.fixture
async def upcoming_fixed_comp(db_session: AsyncSession, test_league: League, test_user: User):
    """Upcoming fixed-teams competition (selection phase open)."""
    comp = Competition(
        name="Fixed Teams Comp",
        mode=CompetitionMode.FIXED_TEAMS,
        status=CompetitionStatus.UPCOMING,
        league_id=test_league.id,
        start_date=datetime.utcnow() + timedelta(days=7),
        end_date=datetime.utcnow() + timedelta(days=30),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        max_teams_per_participant=3,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp


@pytest.fixture
async def participant(db_session: AsyncSession, test_user: User, active_competition: Competition):
    """test_user as participant in active_competition."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def test_game(
    db_session: AsyncSession, active_competition: Competition, test_teams: list[Team]
):
    """Create a test game"""
    game = Game(
        competition_id=active_competition.id,
        external_id="test_game_1",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),  # 2 hours from now
        status=GameStatus.SCHEDULED,
        venue_name="Test Stadium",
        venue_city="Test City",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    return game


async def _login(
    client: AsyncClient, email: str = "test@example.com", password: str = "Password123"
) -> str:
    """Login and return the access token."""
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _login_full(
    client: AsyncClient, email: str = "test@example.com", password: str = "Password123"
) -> dict:
    """Login and return the full token response."""
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.json()


async def _make_global_admin(db_session: AsyncSession, user: User) -> User:
    """Promote user to global admin."""
    user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def invite_link(
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    participant: Participant,
):
    """Invite link created by test_user (who is admin of active_competition).
    is_admin_invite=True because test_user is in league_admin_ids.
    """
    link = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


@pytest.fixture
async def participant_invite_link(
    db_session: AsyncSession, active_competition: Competition, second_user: User
):
    """Invite link created by second_user (regular participant, not admin).
    is_admin_invite=False.
    Requires second_user to be a participant first.
    """
    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    link = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


@pytest.fixture
async def completed_competition(db_session: AsyncSession, test_league: League, test_user: User):
    """Completed competition for testing expired invite links."""
    comp = Competition(
        name="Completed Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.COMPLETED,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow() - timedelta(days=1),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp
