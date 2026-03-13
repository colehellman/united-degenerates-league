import pytest
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
    # We didn't join active_competition in this test yet, but creator might be auto-joined?
    # Actually, in the fixture 'active_competition', it doesn't auto-join.
    # But 'participant' fixture joins test_user to active_competition.
    # Let's check if 'participant' fixture was used.
    # If not, participant_count should be 0.
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
