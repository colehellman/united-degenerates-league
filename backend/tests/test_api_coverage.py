"""
Expanded API test coverage for United Degenerates League.

Covers endpoints not exercised by test_critical_paths.py:
- Auth: refresh, logout
- Users: me, update, change-password, delete, cancel-deletion
- Competitions: get, update, delete, games, available-selections
- Picks: get my-picks, fixed-teams, get fixed-selections
- Admin: join requests (list, approve, reject), audit logs
- Leagues: list
- Health: api-status

Run with: pytest tests/test_api_coverage.py -v
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, AccountStatus
from app.models.competition import (
    Competition, CompetitionMode, CompetitionStatus, Visibility, JoinType,
)
from app.models.league import League, LeagueName, Team
from app.models.game import Game, GameStatus
from app.models.participant import Participant, JoinRequest, JoinRequestStatus
from app.models.pick import Pick, FixedTeamSelection
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash

from tests.conftest import _login, _login_full, _make_global_admin


# ── Auth: Refresh & Logout ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_via_body(client: AsyncClient, test_user: User):
    """Test refreshing tokens by sending refresh_token in request body."""
    tokens = await _login_full(client)
    refresh = tokens["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # New access token should work
    me = await client.get("/api/users/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient, test_user: User):
    """Test that an invalid refresh token is rejected."""
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "garbage.token.value"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_missing(client: AsyncClient):
    """Test that missing refresh token returns 401."""
    resp = await client.post("/api/auth/refresh", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user: User):
    """Test logout clears cookies and returns success."""
    await _login(client)
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out"


# ── Users: Profile ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user: User):
    """GET /users/me returns current user profile."""
    token = await _login(client)
    resp = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["role"] == "user"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """GET /users/me without token returns 401."""
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_username(client: AsyncClient, test_user: User):
    """PATCH /users/me can update username."""
    token = await _login(client)
    resp = await client.patch(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "newname"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "newname"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_user: User):
    """POST /users/me/change-password with correct current password."""
    token = await _login(client)
    resp = await client.post(
        "/api/users/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "Password123", "new_password": "NewPass456"},
    )
    assert resp.status_code == 200

    # Verify new password works
    login_resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "NewPass456"})
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, test_user: User):
    """POST /users/me/change-password with wrong current password returns 400."""
    token = await _login(client)
    resp = await client.post(
        "/api/users/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongPass999", "new_password": "NewPass456"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_account_deletion_and_cancel(client: AsyncClient, test_user: User):
    """DELETE /users/me sets pending deletion; POST cancel-deletion reverts it."""
    token = await _login(client)

    # Request deletion
    del_resp = await client.delete("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 200
    assert del_resp.json()["grace_period_days"] == 30

    # Cancel deletion
    cancel_resp = await client.post("/api/users/me/cancel-deletion", headers={"Authorization": f"Bearer {token}"})
    assert cancel_resp.status_code == 200


@pytest.mark.asyncio
async def test_cancel_deletion_without_pending(client: AsyncClient, test_user: User):
    """POST cancel-deletion when no pending request returns 400."""
    token = await _login(client)
    resp = await client.post("/api/users/me/cancel-deletion", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


# ── Competitions: Get, Update, Delete ────────────────────────────────

@pytest.mark.asyncio
async def test_get_competition_by_id(client: AsyncClient, test_user: User, active_competition: Competition):
    """GET /competitions/{id} returns competition details."""
    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Active Comp"
    assert data["mode"] == "daily_picks"


@pytest.mark.asyncio
async def test_get_competition_not_found(client: AsyncClient, test_user: User):
    """GET /competitions/{bad_id} returns 404."""
    token = await _login(client)
    import uuid
    resp = await client.get(
        f"/api/competitions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_competition_as_global_admin(
    client: AsyncClient, test_user: User, active_competition: Competition, db_session: AsyncSession,
):
    """PATCH /competitions/{id} — global admins can update."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed Comp"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Comp"


@pytest.mark.asyncio
async def test_update_competition_forbidden(
    client: AsyncClient, test_user: User, second_user: User, active_competition: Competition,
):
    """PATCH /competitions/{id} — non-admin gets 403."""
    token = await _login(client, email="second@example.com")
    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Hacked Name"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_competition_as_global_admin(
    client: AsyncClient, test_user: User, active_competition: Competition, db_session: AsyncSession,
):
    """DELETE /competitions/{id} — only global admins can delete."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.delete(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_competition_forbidden_for_regular_user(
    client: AsyncClient, test_user: User, active_competition: Competition,
):
    """DELETE /competitions/{id} — regular user gets 403."""
    token = await _login(client)
    resp = await client.delete(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Competitions: Games ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_competition_games(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], participant: Participant, db_session: AsyncSession,
):
    """GET /competitions/{id}/games returns games list."""
    game = Game(
        competition_id=active_competition.id,
        external_id="game_for_list",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.SCHEDULED,
        venue_name="Test Arena",
        venue_city="Test City",
    )
    db_session.add(game)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["home_team"]["abbreviation"] == "TA"
    assert data[0]["away_team"]["abbreviation"] == "TB"


@pytest.mark.asyncio
async def test_get_competition_games_not_participant(
    client: AsyncClient, test_user: User, second_user: User, active_competition: Competition,
):
    """GET /competitions/{id}/games — non-participant gets 403."""
    token = await _login(client, email="second@example.com")
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Picks: Get My Picks ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_daily_picks(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], participant: Participant, db_session: AsyncSession,
):
    """GET /picks/{id}/my-picks returns user's picks."""
    game = Game(
        competition_id=active_competition.id,
        external_id="game_picks_test",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.SCHEDULED,
        venue_name="Arena", venue_city="City",
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
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/picks/{active_competition.id}/my-picks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["predicted_winner_team_id"] == str(test_teams[0].id)


@pytest.mark.asyncio
async def test_get_my_daily_picks_empty(
    client: AsyncClient, test_user: User, active_competition: Competition, participant: Participant,
):
    """GET /picks/{id}/my-picks with no picks returns empty list."""
    token = await _login(client)
    resp = await client.get(
        f"/api/picks/{active_competition.id}/my-picks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Picks: Fixed Team Selections ─────────────────────────────────────

@pytest.mark.asyncio
async def test_create_fixed_team_selections(
    client: AsyncClient, test_user: User, upcoming_fixed_comp: Competition,
    test_teams: list[Team], db_session: AsyncSession,
):
    """POST /picks/{id}/fixed-teams creates team selections."""
    # Add participant
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client)
    resp = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "selections": [
                {"team_id": str(test_teams[0].id)},
            ]
        },
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert len(data) == 1
    assert data[0]["team_id"] == str(test_teams[0].id)


@pytest.mark.asyncio
async def test_fixed_team_exclusivity(
    client: AsyncClient, test_user: User, second_user: User,
    upcoming_fixed_comp: Competition, test_teams: list[Team], db_session: AsyncSession,
):
    """Fixed team selections enforce exclusivity — same team can't be picked twice."""
    # Both users are participants
    for u in [test_user, second_user]:
        db_session.add(Participant(user_id=u.id, competition_id=upcoming_fixed_comp.id))
    await db_session.commit()

    # First user picks team A
    token1 = await _login(client)
    r1 = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token1}"},
        json={"selections": [{"team_id": str(test_teams[0].id)}]},
    )
    assert r1.status_code == 201

    # Second user tries the same team → 400
    token2 = await _login(client, email="second@example.com")
    r2 = await client.post(
        f"/api/picks/{upcoming_fixed_comp.id}/fixed-teams",
        headers={"Authorization": f"Bearer {token2}"},
        json={"selections": [{"team_id": str(test_teams[0].id)}]},
    )
    assert r2.status_code == 400
    assert "already been selected" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_get_fixed_selections(
    client: AsyncClient, test_user: User, upcoming_fixed_comp: Competition,
    test_teams: list[Team], db_session: AsyncSession,
):
    """GET /picks/{id}/my-fixed-selections returns user's fixed selections."""
    p = Participant(user_id=test_user.id, competition_id=upcoming_fixed_comp.id)
    sel = FixedTeamSelection(
        user_id=test_user.id,
        competition_id=upcoming_fixed_comp.id,
        team_id=test_teams[0].id,
    )
    db_session.add_all([p, sel])
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/picks/{upcoming_fixed_comp.id}/my-fixed-selections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


# ── Admin: Join Requests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_join_requires_approval_creates_request(
    client: AsyncClient, test_user: User, second_user: User,
    approval_competition: Competition, db_session: AsyncSession,
):
    """POST /competitions/{id}/join on requires_approval comp creates a JoinRequest."""
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["user_id"] == str(second_user.id)


@pytest.mark.asyncio
async def test_admin_approve_join_request(
    client: AsyncClient, test_user: User, second_user: User,
    approval_competition: Competition, db_session: AsyncSession,
):
    """Global admin can approve a join request."""
    await _make_global_admin(db_session, test_user)

    # Create a join request
    jr = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(jr)
    await db_session.commit()
    await db_session.refresh(jr)

    token = await _login(client)
    resp = await client.post(
        f"/api/admin/join-requests/{jr.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Verify participant was created
    result = await db_session.execute(
        select(Participant).where(
            Participant.user_id == second_user.id,
            Participant.competition_id == approval_competition.id,
        )
    )
    assert result.scalar_one_or_none() is not None

    # Verify audit log was created
    log_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == AuditAction.JOIN_REQUEST_APPROVED)
    )
    assert log_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_admin_reject_join_request(
    client: AsyncClient, test_user: User, second_user: User,
    approval_competition: Competition, db_session: AsyncSession,
):
    """Global admin can reject a join request."""
    await _make_global_admin(db_session, test_user)

    jr = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(jr)
    await db_session.commit()
    await db_session.refresh(jr)

    token = await _login(client)
    resp = await client.post(
        f"/api/admin/join-requests/{jr.id}/reject",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Verify NOT added as participant
    result = await db_session.execute(
        select(Participant).where(
            Participant.user_id == second_user.id,
            Participant.competition_id == approval_competition.id,
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_list_join_requests_as_global_admin(
    client: AsyncClient, test_user: User, second_user: User,
    approval_competition: Competition, db_session: AsyncSession,
):
    """GET /admin/join-requests/{comp_id} as global admin returns requests."""
    await _make_global_admin(db_session, test_user)

    jr = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(jr)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/admin/join-requests/{approval_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_join_requests_forbidden_for_non_admin(
    client: AsyncClient, test_user: User, second_user: User,
    approval_competition: Competition,
):
    """GET /admin/join-requests/{comp_id} as non-admin returns 403.

    NOTE: This test exposes the str(uuid) vs UUID comparison bug in admin.py.
    The creator IS in league_admin_ids but the check uses str(current_user.id)
    against a list of UUID objects, which always returns False. Only global
    admins can pass the admin check as implemented.
    """
    # 'second_user' is not an admin on this competition
    token = await _login(client, email="second@example.com")
    resp = await client.get(
        f"/api/admin/join-requests/{approval_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Admin: Audit Logs ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_logs_as_global_admin(
    client: AsyncClient, test_user: User, db_session: AsyncSession,
):
    """GET /admin/audit-logs as global admin returns logs."""
    await _make_global_admin(db_session, test_user)

    log = AuditLog(
        admin_user_id=test_user.id,
        action=AuditAction.COMPETITION_CREATED,
        target_type="competition",
        details={"name": "Test"},
    )
    db_session.add(log)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


# ── Leagues ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_leagues(client: AsyncClient, test_user: User, test_league: League):
    """GET /leagues returns all leagues."""
    token = await _login(client)
    resp = await client.get("/api/leagues", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "NFL"
    assert data[0]["is_team_based"] is True


@pytest.mark.asyncio
async def test_list_leagues_unauthenticated(client: AsyncClient):
    """GET /leagues without token returns 401."""
    resp = await client.get("/api/leagues")
    assert resp.status_code == 401


# ── Health ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_api_status(client: AsyncClient, test_user: User):
    """GET /health/api-status returns API health data."""
    token = await _login(client)
    resp = await client.get("/api/health/api-status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_circuit_breakers_forbidden(client: AsyncClient, test_user: User):
    """POST /health/reset-circuit-breakers requires global admin."""
    token = await _login(client)
    resp = await client.post(
        "/api/health/reset-circuit-breakers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reset_circuit_breakers_as_admin(
    client: AsyncClient, test_user: User, db_session: AsyncSession,
):
    """POST /health/reset-circuit-breakers as global admin succeeds."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)
    resp = await client.post(
        "/api/health/reset-circuit-breakers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ── Registration Edge Cases ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Registering with an existing email returns 400."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "uniquename", "password": "StrongPass1"},
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user: User):
    """Registering with an existing username returns 400."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "unique@example.com", "username": "testuser", "password": "StrongPass1"},
    )
    assert resp.status_code == 400
    assert "username" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Password without uppercase or digit is rejected."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "username": "newuser", "password": "nouppercase"},
    )
    assert resp.status_code == 422


# ── Update pick (idempotent) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_existing_pick(
    client: AsyncClient, test_user: User, active_competition: Competition,
    test_teams: list[Team], participant: Participant, db_session: AsyncSession,
):
    """Re-submitting a pick for the same game updates it rather than creating a duplicate."""
    game = Game(
        competition_id=active_competition.id,
        external_id="game_update_test",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime.utcnow() + timedelta(hours=2),
        status=GameStatus.SCHEDULED,
        venue_name="Arena", venue_city="City",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)

    token = await _login(client)

    # Pick team A
    r1 = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={"picks": [{"game_id": str(game.id), "predicted_winner_team_id": str(test_teams[0].id)}]},
    )
    assert r1.status_code == 201

    # Change to team B — same game, different prediction
    r2 = await client.post(
        f"/api/picks/{active_competition.id}/daily",
        headers={"Authorization": f"Bearer {token}"},
        json={"picks": [{"game_id": str(game.id), "predicted_winner_team_id": str(test_teams[1].id)}]},
    )
    assert r2.status_code == 201
    assert r2.json()[0]["predicted_winner_team_id"] == str(test_teams[1].id)

    # Should still only have 1 pick for this game
    result = await db_session.execute(
        select(Pick).where(
            Pick.user_id == test_user.id,
            Pick.game_id == game.id,
        )
    )
    picks = result.scalars().all()
    assert len(picks) == 1
