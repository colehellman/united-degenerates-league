import pytest
import uuid
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.competition import Competition, CompetitionStatus, Visibility, JoinType, CompetitionMode
from app.models.league import League, Team
from app.models.game import Game, GameStatus
from app.models.participant import Participant
from app.models.user import User
from tests.conftest import _login

@pytest.mark.asyncio
async def test_list_competitions_optimized(client: AsyncClient, test_user: User, active_competition: Competition, db_session: AsyncSession):
    """Test the optimized list_competitions endpoint."""
    # Create another competition (private)
    other_comp = Competition(
        name="Private Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=active_competition.league_id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        visibility=Visibility.PRIVATE,
        join_type=JoinType.REQUIRES_APPROVAL,
        creator_id=test_user.id,
    )
    db_session.add(other_comp)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get("/api/competitions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    
    # Should see both (one public, one private but creator is test_user)
    assert len(data) >= 2
    
    # Check participant count and user_is_participant
    comp_ids = [c["id"] for c in data]
    assert str(active_competition.id) in comp_ids
    
    active_resp = next(c for c in data if c["id"] == str(active_competition.id))
    assert active_resp["participant_count"] >= 0

@pytest.mark.asyncio
async def test_get_competition_games_optimized(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], db_session: AsyncSession
):
    """Test the optimized get_competition_games endpoint with H2H pre-fetching."""
    # Join the competition
    participant = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(participant)
    
    # Create some games
    game1 = Game(
        competition_id=active_competition.id,
        external_id="game1",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=1),
        status=GameStatus.SCHEDULED,
    )
    
    # Create a finished game for H2H record
    h2h_game = Game(
        competition_id=active_competition.id,
        external_id="h2h_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(days=2),
        status=GameStatus.FINAL,
        home_team_score=10,
        away_team_score=7,
        winner_team_id=test_teams[0].id,
    )
    
    db_session.add_all([game1, h2h_game])
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    
    # Should see both games
    assert len(data) == 2
    
    # Check H2H record in the future game
    g1_resp = next(g for g in data if g["external_id"] == "game1")
    assert g1_resp["home_team"]["h2h_wins"] == 1
    assert g1_resp["away_team"]["h2h_wins"] == 0

@pytest.mark.asyncio
async def test_create_daily_picks_batch_optimized(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], db_session: AsyncSession
):
    """Test the optimized batch pick creation endpoint."""
    # Join competition
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    
    # Create games
    game1 = Game(
        competition_id=active_competition.id,
        external_id="batch_g1",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.SCHEDULED,
    )
    game2 = Game(
        competition_id=active_competition.id,
        external_id="batch_g2",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=4),
        status=GameStatus.SCHEDULED,
    )
    db_session.add_all([game1, game2])
    await db_session.commit()
    await db_session.refresh(game1)
    await db_session.refresh(game2)

    token = await _login(client)
    
    payload = {
        "picks": [
            {"game_id": str(game1.id), "predicted_winner_team_id": str(test_teams[0].id)},
            {"game_id": str(game2.id), "predicted_winner_team_id": str(test_teams[1].id)},
        ]
    }
    
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    
    # Verify in DB
    result = await db_session.execute(select(Participant).where(Participant.id == p.id))
    p_after = result.scalar_one()
    assert p_after.last_pick_at is not None

@pytest.mark.asyncio
async def test_get_competition_not_found(client: AsyncClient, test_user: User):
    """GET /competitions/{id} returns 404 for non-existent competition."""
    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_join_competition_already_participant(
    client: AsyncClient, test_user: User, active_competition: Competition,
    db_session: AsyncSession
):
    """POST /competitions/{id}/join returns 400 if user is already a participant."""
    # Join first
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
    assert "already a participant" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_update_competition_as_league_admin(
    client: AsyncClient, test_user: User, active_competition: Competition
):
    """PATCH /competitions/{id} returns 200 for league admin (test_user is in league_admin_ids)."""
    token = await _login(client)
    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name"}
    )
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_delete_competition_forbidden(
    client: AsyncClient, test_user: User, active_competition: Competition
):
    """DELETE /competitions/{id} returns 403 for non-admin users."""
    token = await _login(client)
    resp = await client.delete(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_get_available_selections_not_found(client: AsyncClient, test_user: User):
    """GET /competitions/{id}/available-selections returns 404 for non-existent competition."""
    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{uuid.uuid4()}/available-selections",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_create_daily_picks_batch_not_participant(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], db_session: AsyncSession
):
    """POST /api/picks/{id}/daily returns 403 if user is not a participant."""
    game = Game(
        competition_id=active_competition.id,
        external_id="not_participant_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)
    payload = {
        "picks": [
            {"game_id": str(game.id), "predicted_winner_team_id": str(test_teams[0].id)},
        ]
    }
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_daily_picks_batch_game_not_found(
    client: AsyncClient, test_user: User, active_competition: Competition,
    db_session: AsyncSession
):
    """POST /api/picks/{id}/daily returns 404 if game is not found."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    payload = {
        "picks": [
            {"game_id": str(uuid.uuid4()), "predicted_winner_team_id": str(uuid.uuid4())},
        ]
    }
    resp = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_my_daily_picks_invalid_date(
    client: AsyncClient, test_user: User, active_competition: Competition,
    db_session: AsyncSession
):
    """GET /api/picks/{id}/my-picks returns 400 for invalid date format."""
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/picks/{active_competition.id}/my-picks?date=invalid-date",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_get_leaderboard_sorting(
    client: AsyncClient, test_user: User, active_competition: Competition,
    db_session: AsyncSession
):
    """GET /api/leaderboards/{id} with various sort_by options."""
    # Add test user as participant
    p1 = Participant(user_id=test_user.id, competition_id=active_competition.id, total_points=10, total_wins=5, accuracy_percentage=50.0, current_streak=2)
    db_session.add(p1)
    
    # Create another user and participant
    u2 = User(email="u2@example.com", username="user2", hashed_password="...")
    db_session.add(u2)
    await db_session.flush()
    p2 = Participant(user_id=u2.id, competition_id=active_competition.id, total_points=20, total_wins=10, accuracy_percentage=100.0, current_streak=5)
    db_session.add(p2)
    await db_session.commit()

    token = await _login(client)
    
    # Sort by points
    resp = await client.get(f"/api/leaderboards/{active_competition.id}?sort_by=points", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()[0]["user_id"] == str(u2.id) # user2 has 20 points
    
    # Sort by accuracy
    resp = await client.get(f"/api/leaderboards/{active_competition.id}?sort_by=accuracy", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()[0]["accuracy_percentage"] == 100.0
    
    # Sort by wins
    resp = await client.get(f"/api/leaderboards/{active_competition.id}?sort_by=wins", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()[0]["total_wins"] == 10
    
    # Sort by streak
    resp = await client.get(f"/api/leaderboards/{active_competition.id}?sort_by=streak", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()[0]["current_streak"] == 5

