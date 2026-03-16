# Invite Links Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow competition participants to share invite links that let anyone join, with admin-generated links bypassing the `requires_approval` join type.

**Architecture:** New `InviteLink` model with unique tokens. Three new API endpoints (create, list, resolve) plus modifications to the existing join endpoint. New frontend invite landing page and sharing section on competition detail. TDD throughout — every test written and run red before implementation.

**Tech Stack:** FastAPI, SQLAlchemy async (PostgreSQL), Pydantic v2, React 18, TypeScript, TanStack Query, Vitest, pytest (asyncio mode=auto)

**Spec:** `docs/superpowers/specs/2026-03-15-invite-links-design.md`

---

## Chunk 1: Backend Model, Migration, and Fixtures

### Task 1: InviteLink Model

**Files:**
- Create: `backend/app/models/invite_link.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the InviteLink model**

```python
# backend/app/models/invite_link.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import secrets

from app.db.session import Base


class InviteLink(Base):
    """A shareable invite link for a competition."""
    __tablename__ = "invite_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    competition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    token = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(9),
    )
    is_admin_invite = Column(Boolean, nullable=False, default=False)
    use_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    competition = relationship("Competition", back_populates="invite_links")
    created_by = relationship("User")
```

- [ ] **Step 2: Add `invite_links` relationship to Competition model**

In `backend/app/models/competition.py`, add to the Competition class relationships section:

```python
invite_links = relationship("InviteLink", back_populates="competition", cascade="all, delete-orphan")
```

- [ ] **Step 3: Export InviteLink from models __init__**

Add to `backend/app/models/__init__.py`:

```python
from app.models.invite_link import InviteLink
```

And add `"InviteLink"` to the `__all__` list.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/invite_link.py backend/app/models/__init__.py backend/app/models/competition.py
git commit -m "feat: add InviteLink model"
```

### Task 2: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/xxx_add_invite_links.py`
- Modify: `backend/tests/conftest.py` (add invite_links to TRUNCATE)

- [ ] **Step 1: Generate the migration**

```bash
cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "add invite_links table"
```

- [ ] **Step 2: Run the migration**

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

- [ ] **Step 3: Add invite_links to the test TRUNCATE statement**

In `backend/tests/conftest.py`, update the TRUNCATE query (line 43-46) to include `invite_links` before `participants`:

```python
await conn.execute(text(
    "TRUNCATE TABLE picks, fixed_team_selections, join_requests, "
    "invite_links, participants, games, competitions, golfers, teams, "
    "leagues, audit_logs, bug_reports, users CASCADE"
))
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/ backend/tests/conftest.py
git commit -m "feat: add invite_links migration and update test cleanup"
```

### Task 3: Test Fixtures for Invite Links

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add invite link fixtures to conftest.py**

Add at the end of `backend/tests/conftest.py`:

```python
from app.models.invite_link import InviteLink


@pytest.fixture
async def invite_link(db_session: AsyncSession, active_competition: Competition, test_user: User, participant: Participant):
    """Invite link created by test_user (who is admin of active_competition).
    is_admin_invite=True because test_user is in league_admin_ids.
    """
    link = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


@pytest.fixture
async def participant_invite_link(db_session: AsyncSession, active_competition: Competition, second_user: User):
    """Invite link created by second_user (regular participant, not admin).
    is_admin_invite=False.
    Requires second_user to be a participant first.
    """
    p = Participant(user_id=second_user.id, competition_id=active_competition.id)
    db_session.add(p)
    await db_session.commit()

    link = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=second_user.id,
        is_admin_invite=False,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


@pytest.fixture
async def completed_competition(db_session: AsyncSession, test_league: League, test_user: User):
    """Completed competition for testing expired invite links."""
    comp = Competition(
        name="Completed Comp",
        mode=CompetitionMode.DAILY_PICKS,
        status=CompetitionStatus.COMPLETED,
        league_id=test_league.id,
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow() - timedelta(days=1),
        display_timezone="UTC",
        visibility=Visibility.PUBLIC,
        join_type=JoinType.OPEN,
        creator_id=test_user.id,
        league_admin_ids=[test_user.id],
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add invite link and completed competition fixtures"
```

---

## Chunk 2: Backend Model Tests

### Task 4: InviteLink Model Tests

**Files:**
- Create: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/tests/test_invite_links.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -v --tb=short
```

Expected: All 4 tests PASS (model and fixtures already created in Task 1-3).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test: add InviteLink model tests"
```

---

## Chunk 3: Pydantic Schemas

### Task 5: Invite Link Schemas

**Files:**
- Create: `backend/app/schemas/invite_link.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
# backend/app/schemas/invite_link.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

from app.models.competition import CompetitionMode, CompetitionStatus


class InviteLinkResponse(BaseModel):
    """Response for created/listed invite links."""
    id: UUID4
    token: str
    is_admin_invite: bool
    use_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class InviteResolveResponse(BaseModel):
    """Response for resolving an invite token — limited competition info."""
    competition_id: UUID4
    competition_name: str
    description: Optional[str] = None
    league_display_name: str
    mode: CompetitionMode
    status: CompetitionStatus
    participant_count: int
    max_participants: Optional[int] = None
    is_admin_invite: bool


class JoinCompetitionRequest(BaseModel):
    """Optional request body for joining a competition with an invite token."""
    invite_token: Optional[str] = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/invite_link.py
git commit -m "feat: add invite link Pydantic schemas"
```

---

## Chunk 4: Resolve Endpoint (GET /api/invite/{token})

### Task 6: Resolve Endpoint Tests (RED)

**Files:**
- Modify: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write failing resolve endpoint tests**

Append to `backend/tests/test_invite_links.py`:

```python
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
    # Create a participant + invite link for the completed competition
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py::test_resolve_valid_token_returns_competition_info tests/test_invite_links.py::test_resolve_invalid_token_returns_404 tests/test_invite_links.py::test_resolve_completed_competition_returns_410 -v --tb=short
```

Expected: FAIL — 404 for all (endpoint doesn't exist yet).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test(RED): add resolve endpoint tests"
```

### Task 7: Resolve Endpoint Implementation (GREEN)

**Files:**
- Create: `backend/app/api/invite.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the invite router with resolve endpoint**

```python
# backend/app/api/invite.py
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_db
from app.models.invite_link import InviteLink
from app.models.competition import Competition, CompetitionStatus
from app.models.participant import Participant
from app.schemas.invite_link import InviteResolveResponse

router = APIRouter()


@router.get("/{token}", response_model=InviteResolveResponse)
async def resolve_invite_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Resolve an invite token to competition info. No auth required."""
    result = await db.execute(
        select(InviteLink)
        .options(joinedload(InviteLink.competition).joinedload(Competition.league))
        .where(InviteLink.token == token)
    )
    invite_link = result.scalar_one_or_none()

    if not invite_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite link not found",
        )

    competition = invite_link.competition

    if competition.status == CompetitionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This competition has already ended",
        )

    # Count participants
    count_result = await db.execute(
        select(func.count(Participant.id)).where(
            Participant.competition_id == competition.id
        )
    )
    participant_count = count_result.scalar() or 0

    return InviteResolveResponse(
        competition_id=competition.id,
        competition_name=competition.name,
        description=competition.description,
        league_display_name=competition.league.display_name,
        mode=competition.mode,
        status=competition.status,
        participant_count=participant_count,
        max_participants=competition.max_participants,
        is_admin_invite=invite_link.is_admin_invite,
    )
```

- [ ] **Step 2: Register the invite router in main.py**

In `backend/app/main.py`, add the import alongside other router imports:

```python
from app.api import invite
```

And add this line after the other `include_router` calls:

```python
app.include_router(invite.router, prefix="/api/invite", tags=["Invite Links"])
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -v --tb=short
```

Expected: All 7 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/invite.py backend/app/main.py
git commit -m "feat: add invite token resolve endpoint"
```

---

## Chunk 5: Create Invite Link Endpoint (POST /api/competitions/{id}/invite-links)

### Task 8: Create Invite Link Tests (RED)

**Files:**
- Modify: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write failing create endpoint tests**

Append to `backend/tests/test_invite_links.py`:

```python
# ── POST /api/competitions/{id}/invite-links — Create Endpoint ───────────


@pytest.mark.asyncio
async def test_regular_participant_creates_non_admin_invite(
    client: AsyncClient,
    db_session: AsyncSession,
    active_competition: Competition,
    second_user: User,
):
    """A regular participant (not in league_admin_ids) creates is_admin_invite=False."""
    # Make second_user a participant
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
    # Make second_user a participant and global admin
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -k "test_regular_participant_creates or test_league_admin_creates or test_global_admin_creates or test_non_participant_cannot" -v --tb=short
```

Expected: FAIL — 404 or 405 (endpoint doesn't exist).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test(RED): add create invite link endpoint tests"
```

### Task 9: Create Invite Link Implementation (GREEN)

**Files:**
- Modify: `backend/app/api/competitions.py`

- [ ] **Step 1: Add the create invite link endpoint**

Add these imports to the top of `backend/app/api/competitions.py`:

```python
from app.models.invite_link import InviteLink
from app.models.user import UserRole
from app.schemas.invite_link import InviteLinkResponse
```

Then add this endpoint after the existing `join_competition` endpoint (after line ~439):

```python
@router.post("/{competition_id}/invite-links", response_model=InviteLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_invite_link(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a shareable invite link for a competition."""
    # Verify competition exists
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Must be a participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Must be a participant to create an invite link",
        )

    # Determine admin status
    is_admin = (
        current_user.id in (competition.league_admin_ids or [])
        or current_user.role == UserRole.GLOBAL_ADMIN
    )

    invite_link = InviteLink(
        competition_id=competition.id,
        created_by_user_id=current_user.id,
        is_admin_invite=is_admin,
    )
    db.add(invite_link)
    await db.commit()
    await db.refresh(invite_link)

    return InviteLinkResponse.model_validate(invite_link)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -v --tb=short
```

Expected: All 11 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/competitions.py
git commit -m "feat: add create invite link endpoint"
```

---

## Chunk 6: List Invite Links Endpoint (GET /api/competitions/{id}/invite-links)

### Task 10: List Invite Links Tests (RED)

**Files:**
- Modify: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write failing list endpoint tests**

Append to `backend/tests/test_invite_links.py`:

```python
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
    # second_user as participant with their own link
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

    # second_user should only see their own link
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
    # second_user as participant with their own link
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

    # test_user (admin) should see both links
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
    # Most recent first
    assert data[0]["token"] == link2.token
    assert data[1]["token"] == link1.token
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -k "test_participant_sees_own or test_admin_sees_all or test_list_links_sorted" -v --tb=short
```

Expected: FAIL — 405 Method Not Allowed (GET not implemented on that path).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test(RED): add list invite links endpoint tests"
```

### Task 11: List Invite Links Implementation (GREEN)

**Files:**
- Modify: `backend/app/api/competitions.py`

- [ ] **Step 1: Add the list invite links endpoint**

Add this endpoint to `backend/app/api/competitions.py`, after the `create_invite_link` endpoint:

```python
@router.get("/{competition_id}/invite-links", response_model=list[InviteLinkResponse])
async def list_invite_links(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invite links for a competition. Participants see own, admins see all."""
    # Verify competition exists
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Must be a participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Must be a participant to view invite links",
        )

    # Admin sees all, participant sees own
    is_admin = (
        current_user.id in (competition.league_admin_ids or [])
        or current_user.role == UserRole.GLOBAL_ADMIN
    )

    query = select(InviteLink).where(
        InviteLink.competition_id == competition.id
    )
    if not is_admin:
        query = query.where(InviteLink.created_by_user_id == current_user.id)

    query = query.order_by(InviteLink.created_at.desc())

    links_result = await db.execute(query)
    links = links_result.scalars().all()

    return [InviteLinkResponse.model_validate(link) for link in links]
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -v --tb=short
```

Expected: All 14 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/competitions.py
git commit -m "feat: add list invite links endpoint"
```

---

## Chunk 7: Join Endpoint Modifications (POST /api/competitions/{id}/join)

### Task 12: Join with Invite Token Tests (RED)

**Files:**
- Modify: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write failing join endpoint tests**

Append to `backend/tests/test_invite_links.py`:

```python
# ── POST /api/competitions/{id}/join — Join with invite_token ────────────


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
    assert "joined" in resp.json().get("message", "").lower() or resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_invite_bypasses_requires_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_competition: Competition,
    test_user: User,
    second_user: User,
):
    """Admin invite link should bypass requires_approval and join directly."""
    # test_user is admin, create admin invite link
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

    # second_user joins via admin invite
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": link.token},
    )
    assert resp.status_code == 200

    # Verify directly joined as participant (not pending join request)
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
    from app.models.participant import JoinRequest, JoinRequestStatus

    # test_user as participant (not admin for this test — remove from admin_ids)
    # Actually test_user IS the admin. We need a third user to create non-admin link.
    # Use test_user as admin participant, second_user as regular participant who creates link
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
    from app.models.user import User as UserModel, AccountStatus
    from app.core.security import get_password_hash
    third_user = UserModel(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()
    await db_session.refresh(third_user)

    token = await _login(client, email="third@example.com")
    resp = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": link.token},
    )
    assert resp.status_code == 200

    # Should be a join request, not a direct participant
    jr_result = await db_session.execute(
        select(JoinRequest).where(
            and_(
                JoinRequest.competition_id == approval_competition.id,
                JoinRequest.user_id == third_user.id,
            )
        )
    )
    assert jr_result.scalar_one_or_none() is not None

    # Should NOT be a participant
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
    # Create participant + non-admin link
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

    # Third user joins via link
    from app.models.user import User as UserModel, AccountStatus
    from app.core.security import get_password_hash
    third_user = UserModel(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()

    token = await _login(client, email="third@example.com")
    await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
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
    # Create invite link for completed comp
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
    from app.models.participant import JoinRequest, JoinRequestStatus

    # Admin creates link, but second_user uses a non-admin link path
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

    # Third user
    from app.models.user import User as UserModel, AccountStatus
    from app.core.security import get_password_hash
    third_user = UserModel(
        email="third@example.com",
        username="thirduser",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.USER,
        status=AccountStatus.ACTIVE,
    )
    db_session.add(third_user)
    await db_session.commit()

    token = await _login(client, email="third@example.com")

    # First join request
    resp1 = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": link.token},
    )
    assert resp1.status_code == 200

    # Duplicate
    resp2 = await client.post(
        f"/api/competitions/{approval_competition.id}/join",
        headers={"Authorization": f"Bearer {token}"},
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
    # Create a second competition
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

    # Try to join comp2 with invite_link for active_competition
    token = await _login(client, email="second@example.com")
    resp = await client.post(
        f"/api/competitions/{comp2.id}/join",
        headers={"Authorization": f"Bearer {token}"},
        json={"invite_token": invite_link.token},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -k "test_join_without or test_admin_invite_bypasses or test_participant_invite_still or test_use_count_incremented or test_join_completed or test_duplicate_join_request or test_invite_token_from_different" -v --tb=short
```

Expected: Most tests FAIL (join endpoint doesn't accept invite_token body, no status guard, no duplicate check).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test(RED): add join with invite_token tests"
```

### Task 13: Join Endpoint Modifications (GREEN)

**Files:**
- Modify: `backend/app/api/competitions.py`

- [ ] **Step 1: Modify the join endpoint to accept invite_token**

Add this import to the top of `backend/app/api/competitions.py`:

```python
from app.schemas.invite_link import JoinCompetitionRequest
```

Replace the entire `join_competition` function (lines 372-439) with:

```python
@router.post("/{competition_id}/join")
async def join_competition(
    competition_id: str,
    body: Optional[JoinCompetitionRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a competition or request to join. Optionally pass an invite_token."""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Reject joins to completed competitions
    if competition.status == CompetitionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join a completed competition",
        )

    # Check if already a participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a participant",
        )

    # Check if max participants reached
    if competition.max_participants:
        count_result = await db.execute(
            select(func.count(Participant.id)).where(
                Participant.competition_id == competition.id
            )
        )
        if count_result.scalar() >= competition.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competition is full",
            )

    # Validate invite token if provided
    invite_link = None
    invite_token = body.invite_token if body else None
    if invite_token:
        link_result = await db.execute(
            select(InviteLink).where(InviteLink.token == invite_token)
        )
        invite_link = link_result.scalar_one_or_none()

        if not invite_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite token",
            )
        if invite_link.competition_id != competition.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite token is for a different competition",
            )

    # Determine join behavior
    should_join_directly = (
        competition.join_type == "open"
        or (invite_link and invite_link.is_admin_invite)
    )

    if should_join_directly:
        participant = Participant(
            user_id=current_user.id,
            competition_id=competition.id,
        )
        db.add(participant)

        # Atomic use_count increment within the same transaction
        if invite_link:
            await db.execute(
                sa_update(InviteLink)
                .where(InviteLink.id == invite_link.id)
                .values(use_count=InviteLink.use_count + 1)
            )

        await db.commit()
        return {"message": "Joined competition successfully"}

    # Otherwise, create join request (requires_approval path)
    # Check for existing pending join request
    existing_request = await db.execute(
        select(JoinRequest).where(
            and_(
                JoinRequest.competition_id == competition.id,
                JoinRequest.user_id == current_user.id,
                JoinRequest.status == JoinRequestStatus.PENDING,
            )
        )
    )
    if existing_request.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending join request for this competition",
        )

    join_request = JoinRequest(
        user_id=current_user.id,
        competition_id=competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db.add(join_request)

    # Atomic use_count increment within the same transaction
    if invite_link:
        await db.execute(
            sa_update(InviteLink)
            .where(InviteLink.id == invite_link.id)
            .values(use_count=InviteLink.use_count + 1)
        )

    await db.commit()
    await db.refresh(join_request)

    return JoinRequestResponse.model_validate(join_request)
```

Also ensure these imports are at the top of the file (note: `CompetitionStatus`, `UserRole`, and `JoinRequestStatus` are likely already imported — check before adding duplicates):

```python
# Add only if not already present:
from typing import Optional
from fastapi import Body
from sqlalchemy import update as sa_update
from app.models.competition import CompetitionStatus
from app.models.participant import JoinRequestStatus
```

- [ ] **Step 2: Run ALL tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py -v --tb=short
```

Expected: All 22 tests PASS.

- [ ] **Step 3: Run existing competition tests to verify backward compatibility**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_competitions_api.py -v --tb=short
```

Expected: All existing tests still PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/competitions.py
git commit -m "feat: modify join endpoint to support invite tokens"
```

---

## Chunk 8: Atomic use_count Concurrency Test

### Task 14: Concurrency Test

**Files:**
- Modify: `backend/tests/test_invite_links.py`

- [ ] **Step 1: Write concurrency test**

Append to `backend/tests/test_invite_links.py`:

```python
# ── Concurrency ──────────────────────────────────────────────────────────

import asyncio as _asyncio
from sqlalchemy import update as sa_update
from app.db.session import async_session as session_factory


@pytest.mark.asyncio
async def test_use_count_increments_atomically_under_concurrency(
    db_session: AsyncSession,
    active_competition: Competition,
    test_user: User,
    participant: Participant,
):
    """Concurrent increments should not lose updates."""
    link = InviteLink(
        competition_id=active_competition.id,
        created_by_user_id=test_user.id,
        is_admin_invite=True,
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    link_id = link.id

    async def increment():
        async with session_factory() as session:
            await session.execute(
                sa_update(InviteLink)
                .where(InviteLink.id == link_id)
                .values(use_count=InviteLink.use_count + 1)
            )
            await session.commit()

    await _asyncio.gather(*[increment() for _ in range(10)])

    await db_session.refresh(link)
    assert link.use_count == 10
```

- [ ] **Step 2: Run the concurrency test**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_invite_links.py::test_use_count_increments_atomically_under_concurrency -v --tb=short
```

Expected: PASS (we used atomic SQL increment, not ORM-level `+= 1`).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_invite_links.py
git commit -m "test: add atomic use_count concurrency test"
```

---

## Chunk 9: Frontend — Invite Landing Page

### Task 15: InviteLanding Component Tests (RED)

**Files:**
- Create: `frontend/src/pages/InviteLanding.test.tsx`

- [ ] **Step 0: Verify msw is installed (required for API mocking)**

```bash
cd frontend && npm ls msw || npm install -D msw
```

- [ ] **Step 1: Write failing InviteLanding tests**

```typescript
// frontend/src/pages/InviteLanding.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import InviteLanding from './InviteLanding'
import { useAuthStore } from '../services/authStore'

const mockNavigate = vi.fn()

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const server = setupServer(
  http.get('*/api/invite/:token', () => {
    return HttpResponse.json({
      competition_id: '123e4567-e89b-12d3-a456-426614174000',
      competition_name: 'Test Competition',
      description: 'A test competition',
      league_display_name: 'National Football League',
      mode: 'daily_picks',
      status: 'active',
      participant_count: 5,
      max_participants: 20,
      is_admin_invite: false,
    })
  }),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  vi.clearAllMocks()
})
afterAll(() => server.close())

function renderInvite(token = 'abc123', isAuthenticated = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  vi.mocked(useAuthStore).mockReturnValue({
    isAuthenticated,
    isInitializing: false,
    user: isAuthenticated ? { id: 'user-1', email: 'test@example.com', username: 'testuser' } : null,
    checkAuth: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  } as any)

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/invite/${token}`]}>
        <Routes>
          <Route path="/invite/:token" element={<InviteLanding />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('InviteLanding', () => {
  it('shows competition info for unauthenticated user with sign up link', async () => {
    renderInvite('abc123', false)
    await screen.findByText('Test Competition')
    expect(screen.getByText('National Football League')).toBeInTheDocument()
    const signUpLink = screen.getByRole('link', { name: /sign up to join/i })
    expect(signUpLink).toHaveAttribute('href', '/register?redirect=/invite/abc123')
  })

  it('shows join button for authenticated user', async () => {
    renderInvite('abc123', true)
    await screen.findByText('Test Competition')
    expect(screen.getByRole('button', { name: /join competition/i })).toBeInTheDocument()
  })

  it('shows invalid message for unknown token', async () => {
    server.use(
      http.get('*/api/invite/:token', () => {
        return new HttpResponse(null, { status: 404 })
      }),
    )
    renderInvite('badtoken', false)
    await screen.findByText(/invite link is invalid/i)
  })

  it('shows ended message for completed competition', async () => {
    server.use(
      http.get('*/api/invite/:token', () => {
        return new HttpResponse(JSON.stringify({ detail: 'This competition has already ended' }), { status: 410 })
      }),
    )
    renderInvite('oldtoken', false)
    await screen.findByText(/competition has already ended/i)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx vitest run src/pages/InviteLanding.test.tsx
```

Expected: FAIL — `InviteLanding` module doesn't exist.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/InviteLanding.test.tsx
git commit -m "test(RED): add InviteLanding page tests"
```

### Task 16: InviteLanding Component Implementation (GREEN)

**Files:**
- Create: `frontend/src/pages/InviteLanding.tsx`
- Modify: `frontend/src/services/api.ts` (add invite API calls)

- [ ] **Step 1: Add invite API calls to api.ts**

Add these functions at the bottom of `frontend/src/services/api.ts`, before `export default api`:

```typescript
// Invite link API calls
export async function resolveInviteToken(token: string) {
  const resp = await api.get(`/invite/${token}`, { _skipToast: true })
  return resp.data
}

export async function joinViaInvite(competitionId: string, inviteToken: string) {
  const resp = await api.post(`/competitions/${competitionId}/join`, { invite_token: inviteToken })
  return resp.data
}

export async function createInviteLink(competitionId: string) {
  const resp = await api.post(`/competitions/${competitionId}/invite-links`)
  return resp.data
}

export async function listInviteLinks(competitionId: string) {
  const resp = await api.get(`/competitions/${competitionId}/invite-links`)
  return resp.data
}
```

- [ ] **Step 2: Create InviteLanding page**

```typescript
// frontend/src/pages/InviteLanding.tsx
import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../services/authStore'
import { resolveInviteToken, joinViaInvite } from '../services/api'
import Spinner from '../components/Spinner'

export default function InviteLanding() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState('')

  const { data: invite, isLoading, error } = useQuery({
    queryKey: ['invite', token],
    queryFn: () => resolveInviteToken(token!),
    enabled: !!token,
    retry: false,
  })

  const [alreadyParticipant, setAlreadyParticipant] = useState(false)

  const handleJoin = async () => {
    if (!invite || !token) return
    setJoining(true)
    setJoinError('')
    try {
      await joinViaInvite(invite.competition_id, token)
      navigate(`/competitions/${invite.competition_id}`)
    } catch (err: any) {
      const detail = err.response?.data?.detail || ''
      if (detail.toLowerCase().includes('already a participant')) {
        setAlreadyParticipant(true)
      } else {
        setJoinError(detail || 'Failed to join competition')
      }
    } finally {
      setJoining(false)
    }
  }

  if (isLoading) return <Spinner />

  // Error states
  const status = (error as any)?.response?.status
  if (status === 404) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <div className="card max-w-md w-full text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Invalid Link</h2>
          <p className="text-gray-600">This invite link is invalid or has been removed.</p>
          <Link to="/login" className="btn btn-primary mt-6 inline-block">Go to Login</Link>
        </div>
      </div>
    )
  }

  if (status === 410) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <div className="card max-w-md w-full text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Competition Ended</h2>
          <p className="text-gray-600">This competition has already ended.</p>
          <Link to="/login" className="btn btn-primary mt-6 inline-block">Go to Login</Link>
        </div>
      </div>
    )
  }

  if (error || !invite) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <div className="card max-w-md w-full text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-gray-600">Unable to load invite details. Please try again.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="card max-w-md w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">You're Invited!</h1>
        <h2 className="text-lg font-semibold text-gray-700 mb-4">{invite.competition_name}</h2>

        {invite.description && (
          <p className="text-gray-600 mb-4">{invite.description}</p>
        )}

        <div className="space-y-2 text-sm text-gray-600 mb-6">
          <p><span className="font-medium text-gray-700">League:</span> {invite.league_display_name}</p>
          <p><span className="font-medium text-gray-700">Mode:</span> {invite.mode === 'daily_picks' ? 'Daily Picks' : 'Fixed Teams'}</p>
          <p><span className="font-medium text-gray-700">Participants:</span> {invite.participant_count}{invite.max_participants ? ` / ${invite.max_participants}` : ''}</p>
          <p><span className="font-medium text-gray-700">Status:</span> <span className="capitalize">{invite.status}</span></p>
        </div>

        {joinError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
            {joinError}
          </div>
        )}

        {alreadyParticipant ? (
          <div className="text-center">
            <p className="text-gray-600 mb-3">You're already in this competition!</p>
            <Link to={`/competitions/${invite.competition_id}`} className="btn btn-primary inline-block">
              Go to Competition
            </Link>
          </div>
        ) : isAuthenticated ? (
          <button
            onClick={handleJoin}
            disabled={joining}
            className="btn btn-primary w-full"
          >
            {joining ? 'Joining...' : 'Join Competition'}
          </button>
        ) : (
          <Link
            to={`/register?redirect=/invite/${token}`}
            className="btn btn-primary w-full text-center block"
          >
            Sign Up to Join
          </Link>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd frontend && npx vitest run src/pages/InviteLanding.test.tsx
```

Expected: All 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/InviteLanding.tsx frontend/src/pages/InviteLanding.test.tsx frontend/src/services/api.ts
git commit -m "feat: add InviteLanding page and invite API calls"
```

---

## Chunk 10: Frontend — Routing and Auth Redirect

### Task 17: Auth Redirect Tests (RED)

**Files:**
- Modify: `frontend/src/pages/Login.test.tsx`
- Modify: `frontend/src/pages/Register.test.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add redirect tests to Login.test.tsx**

Append to `frontend/src/pages/Login.test.tsx`:

```typescript
describe('Login — redirect param', () => {
  it('navigates to redirect URL after successful login', async () => {
    mockLogin.mockResolvedValueOnce(undefined)

    vi.mocked(useAuthStore).mockReturnValue({ login: mockLogin } as any)
    render(
      <MemoryRouter initialEntries={['/login?redirect=/invite/abc123']}>
        <Login />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'hunter2' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/invite/abc123')
    })
  })
})
```

- [ ] **Step 2: Add redirect tests to Register.test.tsx**

Append to `frontend/src/pages/Register.test.tsx`:

```typescript
describe('Register — redirect param', () => {
  it('navigates to redirect URL after successful registration', async () => {
    mockRegister.mockResolvedValueOnce(undefined)

    vi.mocked(useAuthStore).mockReturnValue({ register: mockRegister } as any)
    render(
      <MemoryRouter initialEntries={['/register?redirect=/invite/abc123']}>
        <Register />
      </MemoryRouter>,
    )

    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/invite/abc123')
    })
  })
})
```

- [ ] **Step 3: Add invite route test to App.test.tsx**

Add the InviteLanding mock alongside other page mocks:

```typescript
vi.mock('./pages/InviteLanding', () => ({ default: () => <div>InviteLanding</div> }))
```

Then append these tests:

```typescript
describe('App — invite route', () => {
  it('renders InviteLanding at /invite/:token when not authenticated', () => {
    currentStore = { isAuthenticated: false }
    renderApp('/invite/abc123')
    expect(screen.getByText('InviteLanding')).toBeInTheDocument()
  })

  it('renders InviteLanding at /invite/:token when authenticated', () => {
    currentStore = { isAuthenticated: true }
    renderApp('/invite/abc123')
    expect(screen.getByText('InviteLanding')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd frontend && npx vitest run src/pages/Login.test.tsx src/pages/Register.test.tsx src/App.test.tsx
```

Expected: Redirect tests FAIL (Login/Register always navigate to `/`). App invite route tests FAIL (route doesn't exist).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Login.test.tsx frontend/src/pages/Register.test.tsx frontend/src/App.test.tsx
git commit -m "test(RED): add auth redirect and invite route tests"
```

### Task 18: Auth Redirect and Route Implementation (GREEN)

**Files:**
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/pages/Register.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add redirect param support to Login.tsx**

In `frontend/src/pages/Login.tsx`, add `useSearchParams` to the import:

```typescript
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
```

Add this line after `const navigate = useNavigate()`:

```typescript
const [searchParams] = useSearchParams()
```

Add a safe redirect helper after the `useSearchParams` line:

```typescript
const redirectTo = (() => {
  const r = searchParams.get('redirect')
  // Prevent open redirect: only allow relative paths
  return r && r.startsWith('/') && !r.startsWith('//') ? r : '/'
})()
```

Change the navigate call in handleSubmit (line 21) from:

```typescript
navigate('/')
```

to:

```typescript
navigate(redirectTo)
```

- [ ] **Step 2: Add redirect param support to Register.tsx**

Same pattern. In `frontend/src/pages/Register.tsx`, add `useSearchParams` to the import:

```typescript
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
```

Add after `const navigate = useNavigate()`:

```typescript
const [searchParams] = useSearchParams()
const redirectTo = (() => {
  const r = searchParams.get('redirect')
  return r && r.startsWith('/') && !r.startsWith('//') ? r : '/'
})()
```

Change the navigate call in handleSubmit (line 43) from:

```typescript
navigate('/')
```

to:

```typescript
navigate(redirectTo)
```

- [ ] **Step 3: Add /invite/:token route and fix auth guard redirects in App.tsx**

Add the imports at the top of `frontend/src/App.tsx`:

```typescript
import InviteLanding from './pages/InviteLanding'
import { useSearchParams } from 'react-router-dom'
```

Inside the `App` component, add after `const location = useLocation()`:

```typescript
const [searchParams] = useSearchParams()
// Prevent open redirect: only allow relative paths
const redirectParam = (() => {
  const r = searchParams.get('redirect')
  return r && r.startsWith('/') && !r.startsWith('//') ? r : null
})()
```

Update the login/register routes to respect the redirect param (lines 60-61). Change:

```typescript
<Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
<Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <Register />} />
```

to:

```typescript
<Route path="/login" element={isAuthenticated ? <Navigate to={redirectParam || "/"} /> : <Login />} />
<Route path="/register" element={isAuthenticated ? <Navigate to={redirectParam || "/"} /> : <Register />} />
```

Add the invite route alongside login/register (after line 61, before the `<Route element={<Layout />}>` block):

```typescript
<Route path="/invite/:token" element={<InviteLanding />} />
```

This places it outside the `<Layout />` wrapper and outside auth guards, so it works for both authenticated and unauthenticated users.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run src/pages/Login.test.tsx src/pages/Register.test.tsx src/App.test.tsx
```

Expected: All tests PASS.

- [ ] **Step 5: Run all frontend tests for regression**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Login.tsx frontend/src/pages/Register.tsx frontend/src/App.tsx
git commit -m "feat: add invite route and auth redirect support"
```

---

## Chunk 11: Frontend — Invite Sharing Section on CompetitionDetail

### Task 19: Invite Sharing Section

**Files:**
- Modify: `frontend/src/pages/CompetitionDetail.tsx`

- [ ] **Step 1: Add invite sharing section to CompetitionDetail**

Add the invite API imports at the top of `frontend/src/pages/CompetitionDetail.tsx`:

```typescript
import { createInviteLink, listInviteLinks } from '../services/api'
```

Note: `useState`, `useQuery`, `useMutation`, `useQueryClient`, `toast`, and `useParams` are already imported in this file. Verify before adding duplicates.

Add invite link state and query inside the `CompetitionDetail` component, after the existing queries:

```typescript
const [inviteCopied, setInviteCopied] = useState(false)

const { data: inviteLinks } = useQuery({
  queryKey: ['invite-links', id],
  queryFn: () => listInviteLinks(id!),
  enabled: !!competition?.user_is_participant,
})

const createInviteMutation = useMutation({
  mutationFn: () => createInviteLink(id!),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['invite-links', id] })
  },
})

const latestInviteLink = inviteLinks?.[0]
const inviteUrl = latestInviteLink
  ? `${window.location.origin}/invite/${latestInviteLink.token}`
  : null

const handleCopyInvite = () => {
  if (inviteUrl) {
    navigator.clipboard.writeText(inviteUrl)
    setInviteCopied(true)
    toast.success('Invite link copied!')
    setTimeout(() => setInviteCopied(false), 2000)
  }
}
```

Add the invite sharing card in the JSX, inside the participant view section (after the competition header/meta info, before the leaderboard). Place it inside a condition `{competition?.user_is_participant && (`:

```tsx
{competition?.user_is_participant && (
  <div className="card mb-6">
    <h3 className="text-lg font-semibold text-gray-900 mb-1">Invite Friends</h3>
    <p className="text-sm text-gray-600 mb-4">
      Copy this link to invite friends. They can join even if they don't have an account yet.
    </p>
    {inviteUrl ? (
      <div className="flex gap-2">
        <input
          type="text"
          readOnly
          value={inviteUrl}
          className="input flex-1 text-sm bg-gray-50"
          onClick={(e) => (e.target as HTMLInputElement).select()}
        />
        <button
          onClick={handleCopyInvite}
          className="btn btn-primary whitespace-nowrap"
        >
          {inviteCopied ? 'Copied!' : 'Copy Link'}
        </button>
      </div>
    ) : (
      <button
        onClick={() => createInviteMutation.mutate()}
        disabled={createInviteMutation.isPending}
        className="btn btn-primary"
      >
        {createInviteMutation.isPending ? 'Generating...' : 'Generate Invite Link'}
      </button>
    )}
  </div>
)}
```

- [ ] **Step 2: Verify build succeeds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CompetitionDetail.tsx
git commit -m "feat: add invite sharing section to competition detail page"
```

---

## Chunk 12: Final Verification

### Task 20: Run All Tests

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v --tb=short
```

Expected: All tests PASS, including existing ones (backward compatibility).

- [ ] **Step 2: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 3: Run frontend lint and build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: No lint errors, build succeeds.

- [ ] **Step 4: Commit any final fixes if needed, then verify git status is clean**

```bash
git status
```
