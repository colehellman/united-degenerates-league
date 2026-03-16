"""Tests for invite link model and API endpoints."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.invite_link import InviteLink
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.models.user import User

from tests.conftest import _login, _login_full, _make_global_admin


# ── Model Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_link_token_is_12_chars(
    db_session: AsyncSession,
    invite_link: InviteLink,
):
    """Token should be 12 characters (secrets.token_urlsafe(9))."""
    assert len(invite_link.token) == 12


@pytest.mark.asyncio
async def test_invite_link_tokens_are_unique(
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    participant: Participant,
):
    """Each invite link should get a unique token."""
    link1 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    link2 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add_all([link1, link2])
    await db_session.commit()
    await db_session.refresh(link1)
    await db_session.refresh(link2)
    assert link1.token != link2.token


@pytest.mark.asyncio
async def test_invite_link_use_count_starts_at_zero(
    db_session: AsyncSession,
    invite_link: InviteLink,
):
    """use_count should default to 0."""
    assert invite_link.use_count == 0


@pytest.mark.asyncio
async def test_cascade_delete_removes_invite_links(
    db_session: AsyncSession,
    active_competition: Competition,
    invite_link: InviteLink,
):
    """Deleting a competition should cascade-delete its invite links."""
    await db_session.delete(active_competition)
    await db_session.commit()
    result = await db_session.execute(select(InviteLink))
    assert result.scalars().all() == []


# ── GET /api/invite/{token} — Resolve Endpoint ──────────────────────────


@pytest.mark.asyncio
async def test_resolve_valid_token_returns_competition_info(
    client: AsyncClient,
    db_session: AsyncSession,
    invite_link: InviteLink,
    active_competition: Competition,
    test_league,
):
    """Resolving a valid token should return competition info (no auth required)."""
    resp = await client.get(f"/api/invite/{invite_link.token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["competition_id"] == str(active_competition.id)
    assert data["competition_name"] == active_competition.name
    assert data["league_display_name"] == test_league.display_name
    assert data["is_admin_invite"] == invite_link.is_admin_invite
    assert "participant_count" in data
    # Verify no game/leaderboard data exposed
    assert "picks" not in data
    assert "scores" not in data
    assert "games" not in data


@pytest.mark.asyncio
async def test_resolve_invalid_token_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Unknown token should return 404."""
    resp = await client.get("/api/invite/doesnotexist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_completed_competition_returns_410(
    client: AsyncClient,
    db_session: AsyncSession,
    completed_competition: Competition,
    test_user: User,
):
    """Token for a completed competition should return 410."""
    p = Participant(user_id=test_user.id, competition_id=completed_competition.id)
    db_session.add(p)
    await db_session.commit()

    link = InviteLink(
        competition_id=completed_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    resp = await client.get(f"/api/invite/{link.token}")
    assert resp.status_code == 410


# ── POST /api/competitions/{id}/invite-links — Create Endpoint ───────────


@pytest.mark.asyncio
async def test_regular_participant_creates_non_admin_invite(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    second_user: User,
):
    """A regular participant (not in league_admin_ids) creates is_admin_invite=False."""
    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin_invite"] is False
    assert len(resp.json()["token"]) == 12


@pytest.mark.asyncio
async def test_league_admin_creates_admin_invite(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    participant: Participant,
):
    """A user in league_admin_ids creates is_admin_invite=True."""
    token = await _login(client)
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin_invite"] is True


@pytest.mark.asyncio
async def test_global_admin_creates_admin_invite(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    second_user: User,
):
    """A global admin (not in league_admin_ids) creates is_admin_invite=True."""
    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()
    await _make_global_admin(db_session, second_user)

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin_invite"] is True


@pytest.mark.asyncio
async def test_non_participant_cannot_create_invite(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    second_user: User,
):
    """A user who is not a participant cannot create an invite link."""
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
