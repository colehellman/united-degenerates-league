import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.competition import Competition
from app.models.participant import JoinRequest, JoinRequestStatus, Participant
from app.models.audit_log import AuditLog, AuditAction
from tests.conftest import _login, _login_full, _make_global_admin

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def join_request(db_session: AsyncSession, second_user: User, approval_competition: Competition):
    """Create a join request from second_user for approval_competition."""
    req = JoinRequest(
        user_id=second_user.id,
        competition_id=approval_competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)
    return req


async def test_get_join_requests_as_admin(
    client: AsyncClient,
    test_user: User,
    approval_competition: Competition,
    join_request: JoinRequest,
):
    """Competition admin must be able to see pending join requests."""
    token = await _login(client, email="test@example.com") # test_user is admin

    response = await client.get(
        f"/api/admin/join-requests/{approval_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(join_request.id)
    assert data[0]["status"] == "pending"
    assert data[0]["user_id"] == str(join_request.user_id)


@pytest.mark.asyncio
async def test_get_audit_logs_with_filters(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    active_competition: Competition,
):
    """GET /admin/audit-logs with filters."""
    await _make_global_admin(db_session, test_user)

    log1 = AuditLog(
        admin_user_id=test_user.id,
        action=AuditAction.COMPETITION_CREATED,
        target_type="competition",
        target_id=active_competition.id,
    )
    log2 = AuditLog(
        admin_user_id=test_user.id, action=AuditAction.USER_DELETED, target_type="user"
    )
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



async def test_get_join_requests_as_non_admin(
    client: AsyncClient,
    second_user: User,
    approval_competition: Competition,
    join_request: JoinRequest,
):
    """A regular user must NOT be able to see join requests."""
    token = await _login(client, email="second@example.com") # second_user is not admin

    response = await client.get(
        f"/api/admin/join-requests/{approval_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_approve_join_request_as_admin(
    client: AsyncClient,
    test_user: User,
    join_request: JoinRequest,
    db_session: AsyncSession,
):
    """Competition admin must be able to approve a join request."""
    token = await _login(client, email="test@example.com")

    response = await client.post(
        f"/api/admin/join-requests/{join_request.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Join request approved"

    # Verify request status
    await db_session.refresh(join_request)
    assert join_request.status == JoinRequestStatus.APPROVED
    assert join_request.reviewed_by_user_id == test_user.id

    # Verify participant was created
    result = await db_session.execute(
        select(Participant).where(
            Participant.user_id == join_request.user_id,
            Participant.competition_id == join_request.competition_id,
        )
    )
    participant = result.scalar_one_or_none()
    assert participant is not None


async def test_reject_join_request_as_admin(
    client: AsyncClient,
    test_user: User,
    join_request: JoinRequest,
    db_session: AsyncSession,
):
    """Competition admin must be able to reject a join request."""
    token = await _login(client, email="test@example.com")

    response = await client.post(
        f"/api/admin/join-requests/{join_request.id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        params={"reason": "Not a good fit"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Join request rejected"

    # Verify request status
    await db_session.refresh(join_request)
    assert join_request.status == JoinRequestStatus.REJECTED
    assert join_request.reviewed_by_user_id == test_user.id
    assert join_request.rejection_reason == "Not a good fit"

    # Verify participant was NOT created
    result = await db_session.execute(
        select(Participant).where(
            Participant.user_id == join_request.user_id,
            Participant.competition_id == join_request.competition_id,
        )
    )
    participant = result.scalar_one_or_none()
    assert participant is None
