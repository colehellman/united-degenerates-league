"""
Tests for admin endpoints that lack coverage:
- PATCH /admin/users/{id}/status
- PATCH /admin/users/{id}/role
- POST /admin/games/{id}/correct-score
- POST /admin/games/{id}/rescore
- POST /admin/competitions/{id}/winner
- DELETE /admin/competitions/{id}/participants/{user_id}
- POST /admin/competitions/{id}/admins
- DELETE /admin/competitions/{id}/admins/{admin_user_id}
- GET /admin/stats
- GET /admin/competitions
- POST /admin/sync-games
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, AccountStatus
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.models.game import Game, GameStatus
from app.models.pick import Pick
from app.models.audit_log import AuditLog, AuditAction
from tests.conftest import _login, _make_global_admin

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# PATCH /admin/users/{id}/status
# ---------------------------------------------------------------------------

async def test_update_user_status_suspend(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """Global admin can suspend a user."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended", "reason": "Violation"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"

    # Verify audit log
    log_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == AuditAction.USER_SUSPENDED)
    )
    assert log_result.scalar_one_or_none() is not None


async def test_update_user_status_ban(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """Global admin can ban a user."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "banned", "reason": "Spam"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "banned"


async def test_update_user_status_reactivate(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """Global admin can reactivate a suspended user."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    # First suspend the user via the API
    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended", "reason": "temp"},
    )
    assert resp.status_code == 200

    # Now reactivate
    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_update_user_status_self_forbidden(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Cannot change your own account status."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{test_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended"},
    )
    assert resp.status_code == 400
    assert "own account" in resp.json()["detail"].lower()


async def test_update_user_status_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """404 for unknown user id."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        "/api/admin/users/00000000-0000-0000-0000-000000000000/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended"},
    )
    assert resp.status_code == 404


async def test_update_user_status_another_global_admin_forbidden(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """Cannot change status of another global admin."""
    await _make_global_admin(db_session, test_user)
    second_user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()

    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended"},
    )
    assert resp.status_code == 400
    assert "global admin" in resp.json()["detail"].lower()


async def test_update_user_status_non_admin_forbidden(
    client: AsyncClient,
    test_user: User,
    second_user: User,
):
    """Regular user cannot change user status."""
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "suspended"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /admin/users/{id}/role
# ---------------------------------------------------------------------------

async def test_update_user_role(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """Global admin can change a user's role."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{second_user.id}/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "global_admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "global_admin"


async def test_update_user_role_self_forbidden(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Cannot change your own role."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/admin/users/{test_user.id}/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "user"},
    )
    assert resp.status_code == 400
    assert "own role" in resp.json()["detail"].lower()


async def test_update_user_role_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """404 for unknown user id."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        "/api/admin/users/00000000-0000-0000-0000-000000000000/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "user"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /admin/games/{id}/correct-score
# ---------------------------------------------------------------------------

async def test_correct_game_score(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Global admin can correct a final game score."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="score_correction_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
        home_team_score=10,
        away_team_score=7,
        winner_team_id=test_teams[0].id,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/correct-score",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "home_team_score": 7,
            "away_team_score": 10,
            "reason": "Scoreboard error",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "corrected" in data["message"].lower()
    assert data["new_score"] == "7-10"


async def test_correct_game_score_not_final(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Cannot correct score of a non-final game."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="not_final_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow(),
        status=GameStatus.IN_PROGRESS,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/correct-score",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_team_score": 1, "away_team_score": 2, "reason": "Test"},
    )
    assert resp.status_code == 400
    assert "final" in resp.json()["detail"].lower()


async def test_correct_game_score_already_corrected(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Cannot correct score more than once."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="already_corrected",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
        home_team_score=10,
        away_team_score=7,
        winner_team_id=test_teams[0].id,
        score_correction_count=1,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/correct-score",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_team_score": 1, "away_team_score": 2, "reason": "Again"},
    )
    assert resp.status_code == 400
    assert "already been corrected" in resp.json()["detail"].lower()


async def test_correct_game_score_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """404 for unknown game id."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/games/00000000-0000-0000-0000-000000000000/correct-score",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_team_score": 1, "away_team_score": 2, "reason": "Test"},
    )
    assert resp.status_code == 404


async def test_correct_game_score_tie(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Score correction resulting in a tie sets winner_team_id to None."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="tie_correction",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
        home_team_score=10,
        away_team_score=7,
        winner_team_id=test_teams[0].id,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/correct-score",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_team_score": 7, "away_team_score": 7, "reason": "Actual tie"},
    )
    assert resp.status_code == 200

    await db_session.refresh(game)
    assert game.winner_team_id is None
    assert game.home_team_score == 7
    assert game.away_team_score == 7


# ---------------------------------------------------------------------------
# POST /admin/games/{id}/rescore
# ---------------------------------------------------------------------------

async def test_rescore_game(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Global admin can re-score picks for a final game."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="rescore_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() - timedelta(hours=3),
        status=GameStatus.FINAL,
        home_team_score=10,
        away_team_score=7,
        winner_team_id=test_teams[0].id,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/rescore",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "re-scored" in resp.json()["message"].lower()


async def test_rescore_game_not_final(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """Cannot rescore a non-final game."""
    await _make_global_admin(db_session, test_user)

    game = Game(
        competition_id=active_competition.id,
        external_id="rescore_scheduled",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=3),
        status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/games/{game.id}/rescore",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_rescore_game_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """404 for unknown game id."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/games/00000000-0000-0000-0000-000000000000/rescore",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /admin/competitions/{id}/winner
# ---------------------------------------------------------------------------

async def test_designate_winner(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Global admin can designate a competition winner."""
    await _make_global_admin(db_session, test_user)

    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)

    resp = await client.post(
        f"/api/admin/competitions/{active_competition.id}/winner",
        headers={"Authorization": f"Bearer {token}"},
        json={"winner_user_id": str(second_user.id), "reason": "Highest score"},
    )
    assert resp.status_code == 200
    assert resp.json()["winner_user_id"] == str(second_user.id)


async def test_designate_winner_not_participant(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Winner must be a participant."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        f"/api/admin/competitions/{active_competition.id}/winner",
        headers={"Authorization": f"Bearer {token}"},
        json={"winner_user_id": str(second_user.id)},
    )
    assert resp.status_code == 400
    assert "participant" in resp.json()["detail"].lower()


async def test_designate_winner_competition_not_found(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
):
    """404 for unknown competition."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/competitions/00000000-0000-0000-0000-000000000000/winner",
        headers={"Authorization": f"Bearer {token}"},
        json={"winner_user_id": str(second_user.id)},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /admin/competitions/{id}/participants/{user_id}
# ---------------------------------------------------------------------------

async def test_remove_participant(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Competition admin can remove a participant."""
    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/participants/{second_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "removed" in resp.json()["message"].lower()


async def test_remove_participant_not_found(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
):
    """404 when participant doesn't exist."""
    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/participants/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_remove_participant_creator_forbidden(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Cannot remove the competition creator."""
    # test_user is the creator and admin; add them as participant
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/participants/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "creator" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /admin/competitions/{id}/admins
# ---------------------------------------------------------------------------

async def test_add_competition_admin(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
):
    """Competition admin can add another admin."""
    token = await _login(client)

    resp = await client.post(
        f"/api/admin/competitions/{active_competition.id}/admins",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": str(second_user.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == str(second_user.id)


async def test_add_competition_admin_already_admin(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
):
    """Cannot add an already-existing admin."""
    token = await _login(client)

    # test_user is already admin (creator)
    resp = await client.post(
        f"/api/admin/competitions/{active_competition.id}/admins",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": str(test_user.id)},
    )
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


async def test_add_competition_admin_user_not_found(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """404 when user to be added doesn't exist."""
    token = await _login(client)

    # Use a valid UUID4 that doesn't match any existing user
    import uuid
    fake_user_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/admin/competitions/{active_competition.id}/admins",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": fake_user_id},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /admin/competitions/{id}/admins/{admin_user_id}
# ---------------------------------------------------------------------------

async def test_remove_competition_admin(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Competition admin can remove another admin."""
    # First add second_user as admin
    active_competition.league_admin_ids = active_competition.league_admin_ids + [second_user.id]
    await db_session.commit()

    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/admins/{second_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "removed" in resp.json()["message"].lower()


async def test_remove_competition_admin_creator_forbidden(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Cannot remove the competition creator as admin."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/admins/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "creator" in resp.json()["detail"].lower()


async def test_remove_competition_admin_not_admin(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
):
    """404 when user to be removed is not an admin."""
    token = await _login(client)

    resp = await client.delete(
        f"/api/admin/competitions/{active_competition.id}/admins/{second_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert "not a competition admin" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------

async def test_platform_stats(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Global admin gets platform stats."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_competitions" in data
    assert "total_competitions" in data
    assert "total_picks" in data
    assert "total_games" in data
    assert data["total_users"] >= 2  # test_user + second_user
    assert data["active_competitions"] >= 1


async def test_platform_stats_non_admin_forbidden(
    client: AsyncClient,
    test_user: User,
):
    """Regular user cannot access platform stats."""
    token = await _login(client)

    resp = await client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/competitions
# ---------------------------------------------------------------------------

async def test_list_all_competitions(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Global admin can list all competitions."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.get(
        "/api/admin/competitions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == active_competition.name
    assert "participant_count" in data[0]


async def test_list_all_competitions_with_status_filter(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Global admin can filter competitions by status."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.get(
        "/api/admin/competitions",
        headers={"Authorization": f"Bearer {token}"},
        params={"status_filter": "active"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["status"] == "active" for c in data)


async def test_list_all_competitions_non_admin_forbidden(
    client: AsyncClient,
    test_user: User,
):
    """Regular user cannot list all competitions via admin endpoint."""
    token = await _login(client)

    resp = await client.get(
        "/api/admin/competitions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/sync-games
# ---------------------------------------------------------------------------

async def test_force_sync_games_admin(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Global admin can trigger game sync."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/sync-games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "sync" in resp.json()["message"].lower()


async def test_force_sync_games_non_admin_forbidden(
    client: AsyncClient,
    test_user: User,
):
    """Regular user cannot trigger game sync."""
    token = await _login(client)

    resp = await client.post(
        "/api/admin/sync-games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Competition status change (admin endpoint, additional branches)
# ---------------------------------------------------------------------------

async def test_force_competition_status_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """404 for unknown competition."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/competitions/00000000-0000-0000-0000-000000000000/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "completed"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Users.py coverage: duplicate username via PATCH /users/me
# ---------------------------------------------------------------------------

async def test_update_username_duplicate(
    client: AsyncClient,
    test_user: User,
    second_user: User,
):
    """PATCH /users/me with an already-taken username returns 400."""
    token = await _login(client)

    resp = await client.patch(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": second_user.username},
    )
    assert resp.status_code == 400
    assert "username" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Competitions.py coverage: list competitions with filters
# ---------------------------------------------------------------------------

async def test_list_competitions_with_status_filter(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
):
    """GET /competitions with status_filter returns filtered results."""
    token = await _login(client)

    resp = await client.get(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        params={"status_filter": "active"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["status"] == "active" for c in data)


async def test_list_competitions_with_visibility_filter(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
):
    """GET /competitions with visibility filter."""
    token = await _login(client)

    resp = await client.get(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        params={"visibility": "public"},
    )
    assert resp.status_code == 200


async def test_get_competition_games_invalid_date(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    participant: Participant,
):
    """GET /competitions/{id}/games with invalid date format returns 400."""
    token = await _login(client)

    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"},
        params={"date": "not-a-date"},
    )
    assert resp.status_code == 400
    assert "date format" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Join request edge cases
# ---------------------------------------------------------------------------

async def test_join_request_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Approve non-existent join request returns 404."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/join-requests/00000000-0000-0000-0000-000000000000/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_reject_join_request_not_found(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Reject non-existent join request returns 404."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.post(
        "/api/admin/join-requests/00000000-0000-0000-0000-000000000000/reject",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
