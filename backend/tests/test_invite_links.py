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
