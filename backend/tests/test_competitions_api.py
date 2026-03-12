import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
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


@pytest.mark.asyncio
async def test_sync_competition_games_admin_success(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
):
    """Competition admin can trigger sync; endpoint returns created/updated counts."""
    token = await _login(client)
    mock_result = {"created": 3, "updated": 1}

    # Patch at the source module so the local import inside the endpoint resolves to the mock.
    with patch(
        "app.services.background_jobs.sync_games_for_competition",
        new=AsyncMock(return_value=mock_result),
    ):
        resp = await client.post(
            f"/api/competitions/{active_competition.id}/sync-games",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json() == mock_result


@pytest.mark.asyncio
async def test_sync_competition_games_non_admin_forbidden(
    client: AsyncClient,
    second_user: User,
    active_competition: Competition,
):
    """Non-admin user cannot trigger game sync — 403."""
    token = await _login(client, email="second@example.com")

    resp = await client.post(
        f"/api/competitions/{active_competition.id}/sync-games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sync_competition_games_not_found(
    client: AsyncClient,
    test_user: User,
):
    """Sync endpoint returns 404 for unknown competition id."""
    token = await _login(client)

    resp = await client.post(
        "/api/competitions/00000000-0000-0000-0000-000000000000/sync-games",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_competition_with_tz_aware_dates(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    db_session: AsyncSession,
):
    """PATCH with tz-aware ISO dates exercises the CompetitionUpdate strip_timezone validator.

    update_competition uses str(current_user.id) comparison so we elevate to
    global admin (same workaround used by test_update_competition_status).
    """
    await _make_global_admin(db_session, test_user)
    token = await _login(client)
    future = (datetime.now(tz=timezone.utc) + timedelta(days=14)).isoformat()

    resp = await client.patch(
        f"/api/competitions/{active_competition.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"end_date": future},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_games_date_filter_respects_utc_offset(
    client: AsyncClient,
    test_user: User,
    active_competition: Competition,
    test_teams: list,
    db_session: AsyncSession,
):
    """UTC offset parameter must shift the date window so a late-evening local
    game (stored past midnight UTC) is included in the correct local date.

    Root cause of the date-mismatch bug: a 9pm ET game on 2026-03-08 is stored
    as 2026-03-09 02:00 UTC. Without utc_offset_minutes the filter window is
    2026-03-08 00:00–23:59 UTC, which excludes it.  With offset=300 (EST) the
    window becomes 2026-03-08 05:00 → 2026-03-09 04:59 UTC, which includes it.
    """
    from app.models.participant import Participant
    from app.models.game import Game, GameStatus

    # Make test_user a participant so the endpoint allows access.
    p = Participant(user_id=test_user.id, competition_id=active_competition.id)
    db_session.add(p)

    # 9pm ET on 2026-03-08 = 02:00 UTC on 2026-03-09 (naive, as stored by ESPN)
    late_evening_game = Game(
        competition_id=active_competition.id,
        external_id="tz_test_game",
        home_team_id=test_teams[0].id,
        away_team_id=test_teams[1].id,
        scheduled_start_time=datetime(2026, 3, 9, 2, 0, 0),  # UTC naive
        status=GameStatus.SCHEDULED,
        spread=-7.5,
    )
    db_session.add(late_evening_game)
    await db_session.commit()

    token = await _login(client)

    # Without offset: UTC window 2026-03-08 00:00→23:59 — game at 02:00 on 9th
    # is OUTSIDE the window and must not be returned.
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"},
        params={"date": "2026-03-08", "utc_offset_minutes": 0},
    )
    assert resp.status_code == 200
    ids_no_offset = [g["id"] for g in resp.json()]
    assert str(late_evening_game.id) not in ids_no_offset, (
        "Game should NOT appear without timezone offset (it falls on 2026-03-09 UTC)"
    )

    # With EST offset (300 min west): window shifts to 2026-03-08 05:00 →
    # 2026-03-09 04:59 UTC — game at 02:00 on 9th IS inside the window.
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/games",
        headers={"Authorization": f"Bearer {token}"},
        params={"date": "2026-03-08", "utc_offset_minutes": 300},
    )
    assert resp.status_code == 200
    games_with_offset = resp.json()
    ids_with_offset = [g["id"] for g in games_with_offset]
    assert str(late_evening_game.id) in ids_with_offset, (
        "Game MUST appear when EST offset is supplied (9pm ET = 2am UTC on the 9th)"
    )
    # Check that the spread is correctly serialized in the response
    game_data = next((g for g in games_with_offset if g['id'] == str(late_evening_game.id)), None)
    assert game_data is not None
    assert "spread" in game_data
    assert game_data["spread"] == -7.5
