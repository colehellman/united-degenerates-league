import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.competition import Competition, CompetitionStatus
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
