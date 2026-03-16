"""Tests for invite link model and API endpoints."""
import pytest
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.invite_link import InviteLink
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.models.user import User, UserRole

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


# ── GET /api/competitions/{id}/invite-links — List Endpoint ──────────────


@pytest.mark.asyncio
async def test_participant_sees_own_links_only(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    second_user: User,
    participant: Participant,
):
    """A regular participant should only see their own invite links."""
    p2 = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p2)
    await db_session.commit()

    link_user1 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    link_user2 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add_all([link_user1, link_user2])
    await db_session.commit()

    token = await _login(client, email="second@example.com")
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["is_admin_invite"] is False


@pytest.mark.asyncio
async def test_admin_sees_all_links(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    second_user: User,
    participant: Participant,
):
    """An admin should see all invite links for the competition."""
    p2 = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p2)
    await db_session.commit()

    link_admin = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    link_user = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add_all([link_admin, link_user])
    await db_session.commit()

    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_links_sorted_by_created_at_desc(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    participant: Participant,
):
    """Links should be returned sorted by created_at DESC (most recent first)."""
    link1 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link1)
    await db_session.commit()
    await db_session.refresh(link1)

    link2 = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link2)
    await db_session.commit()
    await db_session.refresh(link2)

    token = await _login(client)
    resp = await client.get(
        f"/api/competitions/{active_competition.id}/invite-links",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["token"] == link2.token
    assert data[1]["token"] == link1.token


# ── POST /api/competitions/{id}/join — Join with invite_token ────────────

from datetime import datetime, timedelta
from app.models.competition import CompetitionMode, Visibility, JoinType


@pytest.mark.asyncio
async def test_join_without_invite_token_still_works(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    second_user: User,
):
    """Backward compat: joining without invite_token should still work."""
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_invite_bypasses_requires_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_competition: Competition,
    test_user: User,
    second_user: User,
):
    """Admin invite link should bypass requires_approval and join directly."""
    p_admin = Participant(user_id=test_user.id, competition_id=approval_competition.id)
    db_session.add(p_admin)
    await db_session.commit()

    link = InviteLink(
        competition_id=approval_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": link.token},
    )
    assert resp.status_code == 200

    participant_result = await db_session.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == approval_competition.id,
                Participant.user_id == second_user.id,
            )
        )
    )
    assert participant_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_participant_invite_still_requires_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_competition: Competition,
    test_user: User,
    second_user: User,
):
    """Non-admin invite on requires_approval competition should create join request."""
    from app.models.participant import JoinRequest as JR

    p_admin = Participant(user_id=test_user.id, competition_id=approval_competition.id)
    p_regular = Participant(user_id=second_user.id, competition_id=approval_competition.id)
    db_session.add_all([p_admin, p_regular])
    await db_session.commit()

    link = InviteLink(
        competition_id=approval_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    # Create a third user to join via the non-admin link
    from app.core.security import get_password_hash
    from app.models.user import AccountStatus
    third_user = User(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()
    await db_session.refresh(third_user)

    login_token = await _login(client, email="third@example.com")
    resp = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"invite_token": link.token},
    )
    assert resp.status_code == 200

    # Should be a join request, not a direct participant
    jr_result = await db_session.execute(
        select(JR).where(
            and_(
                JR.competition_id == approval_competition.id,
                JR.user_id == third_user.id,
            )
        )
    )
    assert jr_result.scalar_one_or_none() is not None

    p_result = await db_session.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == approval_competition.id,
                Participant.user_id == third_user.id,
            )
        )
    )
    assert p_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_use_count_incremented_after_join(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    invite_link: InviteLink,
    second_user: User,
):
    """use_count should increment when someone joins via the link."""
    assert invite_link.use_count == 0

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{active_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": invite_link.token},
    )
    assert resp.status_code == 200

    await db_session.refresh(invite_link)
    assert invite_link.use_count == 1


@pytest.mark.asyncio
async def test_use_count_incremented_after_join_request(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_competition: Competition,
    test_user: User,
    second_user: User,
):
    """use_count should increment even for join requests (requires_approval)."""
    p = Participant(user_id=second_user.id, competition_id=approval_competition.id)
    db_session.add(p)
    await db_session.commit()

    link = InviteLink(
        competition_id=approval_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    from app.core.security import get_password_hash
    from app.models.user import AccountStatus
    third_user = User(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()

    login_token = await _login(client, email="third@example.com")
    await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"invite_token": link.token},
    )

    await db_session.refresh(link)
    assert link.use_count == 1


@pytest.mark.asyncio
async def test_join_completed_competition_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    completed_competition: Competition,
    test_user: User,
    second_user: User,
):
    """Joining a completed competition should be rejected."""
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

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{completed_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": link.token},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_join_request_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_competition: Competition,
    test_user: User,
    second_user: User,
):
    """Duplicate join request should return 409."""
    p = Participant(user_id=second_user.id, competition_id=approval_competition.id)
    db_session.add(p)
    await db_session.commit()

    link = InviteLink(
        competition_id=approval_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    from app.core.security import get_password_hash
    from app.models.user import AccountStatus
    third_user = User(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()

    login_token = await _login(client, email="third@example.com")

    resp1 = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"invite_token": link.token},
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"invite_token": link.token},
    )
    assert resp2.status_code == 409
    assert "pending" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invite_token_from_different_competition_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    second_user: User,
    invite_link: InviteLink,
    test_league_2,
):
    """Using an invite token for a different competition should be rejected."""
    comp2 = Competition(
        name="Other Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.ACTIVE,
        league_id=test_league_2.id,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=7),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp2)
    await db_session.commit()
    await db_session.refresh(comp2)

    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{comp2.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": invite_link.token},
    )
    assert resp.status_code == 400
