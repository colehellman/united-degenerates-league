import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.competition import Competition, CompetitionMode, CompetitionStatus, Visibility, JoinType
from app.models.league import League, LeagueName, Team
from app.models.participant import Participant, JoinRequest, JoinRequestStatus
from app.models.audit_log import AuditLog, AuditAction
from tests.conftest import _login, _make_global_admin

@pytest.mark.asyncio
async def test_create_competition_invalid_dates(client: AsyncClient, test_user: User, test_league: League):
    """Test creating a competition with an end date before the start date."""
    token = await _login(client)
    resp = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Invalid Dates Comp",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "visibility": "public",
            "join_type": "open",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_join_full_competition(client: AsyncClient, test_user: User, second_user: User, active_competition: Competition, db_session: AsyncSession):
    """Test joining a competition that is already full."""
    active_competition.max_participants = 1
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "full" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_join_competition_already_participant(client: AsyncClient, test_user: User, active_competition: Competition, participant: Participant):
    """Test joining a competition the user is already a part of."""
    token = await _login(client)
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "already a participant" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_competition_as_unauthenticated_user(client: AsyncClient, test_league: League):
    """Test creating a competition as an unauthenticated user."""
    resp = await client.post(
        "/api/competitions",
        json={
            "name": "Unauthorized Comp",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "visibility": "public",
            "join_type": "open",
        },
    )
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_update_competition_as_non_admin(client: AsyncClient, second_user: User, active_competition: Competition):
    """Test updating a competition as a non-admin user."""
    token = await _login(client, email="second@example.com")
    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name"},
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_delete_competition_as_league_admin(client: AsyncClient, test_user: User, active_competition: Competition):
    """Test deleting a competition as a league admin (should be forbidden)."""
    token = await _login(client)
    resp = await client.delete(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_pick_not_participant(client: AsyncClient, second_user: User, active_competition: Competition):
    """Test creating a pick for a competition the user is not a part of."""
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={"picks": [{"game_id": "some_game_id", "predicted_winner_team_id": "some_team_id"}]},
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_create_pick_for_started_game(client: AsyncClient, test_user: User, active_competition: Competition, test_teams, participant, db_session: AsyncSession):
    """Test creating a pick for a game that has already started."""
    from app.models.game import Game, GameStatus
    game = Game(
        competition_id=active_competition.id,
        external_id="started_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=1),
        status=GameStatus.IN_PROGRESS,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={"picks": [{"game_id": str(game.id), "predicted_winner_team_id": str(test_teams[0].id)}]},
    )
    assert resp.status_code == 400
    assert "has already started" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_create_pick_exceeds_daily_limit(client: AsyncClient, test_user: User, active_competition: Competition, test_teams, participant, db_session: AsyncSession):
    """Submitting a batch larger than max_picks_per_day must be rejected.

    With replace semantics a second *single-game* submission would simply
    swap the existing pick (still 1 total → OK).  The limit is enforced
    against the incoming batch size, so sending 2 picks when cap is 1
    must still return 400.
    """
    active_competition.max_picks_per_day = 1
    await db_session.commit()

    from app.models.game import Game
    game1 = Game(competition_id=active_competition.id, external_id="game1", home_team_id=test_teams[0].id, away_team_id=test_teams[1].id, scheduled_start_time=datetime.utcnow() + timedelta(hours=2))
    game2 = Game(competition_id=active_competition.id, external_id="game2", home_team_id=test_teams[0].id, away_team_id=test_teams[1].id, scheduled_start_time=datetime.utcnow() + timedelta(hours=3))
    db_session.add_all([game1, game2])
    await db_session.commit()
    await db_session.refresh(game1)
    await db_session.refresh(game2)

    token = await _login(client)

    # Submitting 2 games in a single batch when the cap is 1 must fail.
    # (locked_started_picks=0 + batch_size=2 = 2 > 1)
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={"picks": [
            {"game_id": str(game1.id), "predicted_winner_team_id": str(test_teams[0].id)},
            {"game_id": str(game2.id), "predicted_winner_team_id": str(test_teams[0].id)},
        ]},
    )
    assert resp.status_code == 400
    assert "daily pick limit" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_fixed_selection_for_started_competition(client: AsyncClient, test_user: User, upcoming_fixed_comp: Competition, test_teams, db_session: AsyncSession):
    """Test creating a fixed team selection for a competition that has already started."""
    upcoming_fixed_comp.start_date = datetime.utcnow() - timedelta(days=1)
    await db_session.commit()
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    resp = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token}"},
        json={"selections": [{"team_id": str(test_teams[0].id)}]},
    )
    assert resp.status_code == 400
    assert "selection phase has ended" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_fixed_selection_exceeds_limit(client: AsyncClient, test_user: User, upcoming_fixed_comp: Competition, test_teams, db_session: AsyncSession):
    """Test creating a fixed team selection that exceeds the limit."""
    upcoming_fixed_comp.max_teams_per_participant = 1
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    # First selection
    await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token}"},
        json={"selections": [{"team_id": str(test_teams[0].id)}]},
    )
    # Second selection should fail
    resp = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token}"},
        json={"selections": [{"team_id": str(test_teams[1].id)}]},
    )
    assert resp.status_code == 400
    assert "maximum selections" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_fixed_selection_with_both_team_and_golfer(client: AsyncClient, test_user: User, upcoming_fixed_comp: Competition, test_teams, db_session: AsyncSession):
    """Test creating a fixed team selection with both team_id and golfer_id."""
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    resp = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token}"},
        json={"selections": [{"team_id": str(test_teams[0].id), "golfer_id": "some_golfer_id"}]},
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_approve_join_request_as_non_admin(client: AsyncClient, second_user: User, approval_competition: Competition, db_session: AsyncSession):
    """Test approving a join request by a non-admin."""
    jr = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(jr)
    await db_session.commit()
    await db_session.refresh(jr)
    
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/admin/join-requests/{jr.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_approve_already_approved_join_request(client: AsyncClient, test_user: User, second_user: User, approval_competition: Competition, db_session: AsyncSession):
    """Test approving an already approved join request."""
    await _make_global_admin(db_session, test_user)
    jr = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.APPROVED,
    )
    db_session.add(jr)
    await db_session.commit()
    await db_session.refresh(jr)

    token = await _login(client)
    resp = await client.post(
        f"/api/admin/join-requests/{jr.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "not pending" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_list_audit_logs_as_non_admin(client: AsyncClient, second_user: User):
    """Test listing audit logs as a non-admin."""
    token = await _login(client, email="second@example.com")
    resp = await client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_audit_logs_with_filters(client: AsyncClient, test_user: User, db_session: AsyncSession, active_competition: Competition):
    """GET /admin/audit-logs with filters."""
    await _make_global_admin(db_session, test_user)

    log1 = AuditLog(admin_user_id=test_user.id, action=AuditAction.COMPETITION_CREATED, target_type="competition", target_id=active_competition.id)
    log2 = AuditLog(admin_user_id=test_user.id, action=AuditAction.USER_DELETED, target_type="user")
    db_session.add_all([log1, log2])
    await db_session.commit()

    token = await _login(client)
    # Filter by action
    resp = await client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
        params={"action_filter": "competition_created"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "competition_created"

    # Filter by competition
    resp = await client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
        params={"competition_id": str(active_competition.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["target_id"] == str(active_competition.id)

@pytest.mark.asyncio
async def test_get_leaderboard_not_found(client: AsyncClient, test_user: User):
    """Test getting a leaderboard for a competition that doesn't exist."""
    token = await _login(client)
    import uuid
    resp = await client.get(
        f"/api/leaderboards/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_leaderboard_not_participant(client: AsyncClient, second_user: User, active_competition: Competition, db_session: AsyncSession):
    """Test getting a leaderboard for a private competition the user is not a part of."""
    active_competition.visibility = Visibility.PRIVATE
    await db_session.commit()
    
    token = await _login(client, email="second@example.com")
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_get_leaderboard_with_sort(client: AsyncClient, test_user: User, active_competition: Competition, participant: Participant):
    """Test getting a leaderboard with different sort options."""
    token = await _login(client)
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"sort_by": "accuracy"},
    )
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_leagues_unauthenticated(client: AsyncClient):
    """Test getting leagues with an unauthenticated user."""
    resp = await client.get("/api/leagues")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_get_leaderboard_sorted(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Leaderboard can be sorted by different valid fields."""
    # Create some participants with varying stats
    p1 = Participant(user_id=test_user.id, competition_id=active_competition.id, total_points=10, accuracy_percentage=50.0, total_wins=5, current_streak=2)
    
    # Need another user for the leaderboard
    from app.models.user import User as UserModel, UserRole, AccountStatus
    from app.core.security import get_password_hash
    other_user = UserModel(email="other@example.com", username="otheruser", hashed_password=get_password_hash("password"), role=UserRole.USER, status=AccountStatus.ACTIVE)
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    
    p2 = Participant(user_id=other_user.id, competition_id=active_competition.id, total_points=20, accuracy_percentage=75.0, total_wins=10, current_streak=5)
    db_session.add_all([p1, p2])
    await db_session.commit()

    token = await _login(client)

    # Sort by points (default)
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["user_id"] == str(p2.user_id) # p2 has more points

    # Sort by accuracy
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}?sort_by=accuracy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["user_id"] == str(p2.user_id) # p2 has higher accuracy

    # Sort by wins
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}?sort_by=wins",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["user_id"] == str(p2.user_id) # p2 has more wins

    # Sort by streak
    resp = await client.get(
        f"/api/leaderboards/{active_competition.id}?sort_by=streak",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["user_id"] == str(p2.user_id) # p2 has a better streak
