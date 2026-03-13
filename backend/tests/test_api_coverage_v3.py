import pytest
import uuid
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, AccountStatus
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import JoinRequest, JoinRequestStatus, Participant
from tests.conftest import _login

@pytest.mark.asyncio
async def test_get_join_requests_not_found(client: AsyncClient, test_user: User):
    """GET /api/admin/join-requests/{id} returns 404 for non-existent competition."""
    token = await _login(client)
    resp = await client.get(
        f"/api/admin/join-requests/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_approve_join_request_not_found(client: AsyncClient, test_user: User):
    """POST /api/admin/join-requests/{id}/approve returns 404 for non-existent request."""
    token = await _login(client)
    resp = await client.post(
        f"/api/admin/join-requests/{uuid.uuid4()}/approve",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """GET /api/admin/users requires global admin role."""
    test_user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

@pytest.mark.asyncio
async def test_auth_refresh_invalid(client: AsyncClient):
    """POST /api/auth/refresh returns 401 for invalid token."""
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid-token"}
    )
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_force_sync_games_as_admin(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """POST /api/admin/sync-games requires global admin role."""
    test_user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()

    token = await _login(client)
    resp = await client.post(
        "/api/admin/sync-games",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Game sync triggered"

@pytest.mark.asyncio
async def test_reject_join_request_forbidden(client: AsyncClient, test_user: User, db_session: AsyncSession, test_league):
    """POST /api/admin/join-requests/{id}/reject returns 403 for non-admin."""
    # Create another user to be the admin
    u_admin = User(email="admin_reject@example.com", username="admin_reject", hashed_password="...")
    db_session.add(u_admin)
    await db_session.flush()
    
    # Create competition where test_user is NOT admin
    comp = Competition(
        name="Private Comp Reject",
        mode="daily_picks",
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        creator_id=u_admin.id,
        league_admin_ids=[u_admin.id],
    )
    db_session.add(comp)
    await db_session.flush()
    
    # Create a join request for another user
    u2 = User(email="u2_reject@example.com", username="u2_reject", hashed_password="...")
    db_session.add(u2)
    await db_session.flush()
    req = JoinRequest(user_id=u2.id, competition_id=comp.id)
    db_session.add(req)
    await db_session.commit()

    token = await _login(client) # test_user
    resp = await client.post(
        f"/api/admin/join-requests/{req.id}/reject",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_update_bug_report_status_not_found(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """PATCH /api/bug-reports/{id} returns 404 for non-existent report."""
    test_user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()

    token = await _login(client)
    resp = await client.patch(
        f"/api/bug-reports/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_list_participants_not_found(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """GET /api/admin/competitions/{id}/participants returns 404."""
    test_user.role = UserRole.GLOBAL_ADMIN
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/admin/competitions/{uuid.uuid4()}/participants",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_list_participants_forbidden(client: AsyncClient, test_user: User, db_session: AsyncSession, test_league):
    """GET /api/admin/competitions/{id}/participants returns 403."""
    # Create another user to be the admin
    u_admin = User(email="admin_list@example.com", username="admin_list", hashed_password="...")
    db_session.add(u_admin)
    await db_session.flush()

    # Create comp where test_user is not admin
    comp = Competition(
        name="Forbidden Participants List",
        mode="daily_picks",
        status=CompetitionStatus.ACTIVE,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        creator_id=u_admin.id,
        league_admin_ids=[],
    )
    db_session.add(comp)
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/admin/competitions/{comp.id}/participants",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
