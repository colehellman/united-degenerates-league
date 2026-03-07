import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.competition import Competition, CompetitionStatus
from app.models.league import League
from tests.conftest import _login, _make_global_admin


@pytest.mark.asyncio
async def test_update_competition_status(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """Test updating competition status."""
    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    # From ACTIVE to COMPLETED
    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    await db_session.refresh(active_competition)
    assert active_competition.status == CompetitionStatus.COMPLETED


@pytest.mark.asyncio
async def test_create_competition_past_start_date_rejected(
    client: AsyncClient,
    test_user: User,
    test_league: League,
):
    """start_date in the past must return 422."""
    token = await _login(client)
    past = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    resp = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Past Start Comp",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": past,
            "end_date": future,
            "visibility": "public",
            "join_type": "open",
        },
    )
    assert resp.status_code == 422
    # Pydantic surfaces the validator message somewhere in the detail
    detail = resp.json()["detail"]
    assert any("past" in str(d).lower() for d in (detail if isinstance(detail, list) else [detail]))


@pytest.mark.asyncio
async def test_create_competition_future_start_date_accepted(
    client: AsyncClient,
    test_user: User,
    test_league: League,
):
    """start_date in the future must create successfully with UPCOMING status."""
    token = await _login(client)
    future_start = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    future_end = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    resp = await client.post(
        "/api/competitions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Future Start Comp",
            "mode": "daily_picks",
            "league_id": str(test_league.id),
            "start_date": future_start,
            "end_date": future_end,
            "visibility": "public",
            "join_type": "open",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "upcoming"
    assert data["name"] == "Future Start Comp"
