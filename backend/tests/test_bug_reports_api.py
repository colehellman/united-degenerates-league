"""Tests for the /api/bug-reports endpoints."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import _login, _make_global_admin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _submit_report(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {
        "title": "Button does not work",
        "description": "Clicking the submit button does nothing on the picks page.",
        "category": "ui",
        **overrides,
    }
    resp = await client.post(
        "/api/bug-reports",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


# ---------------------------------------------------------------------------
# POST /api/bug-reports
# ---------------------------------------------------------------------------


async def test_submit_bug_report_success(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    resp = await _submit_report(client, token)

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Button does not work"
    assert data["status"] == "open"
    assert data["category"] == "ui"
    assert data["user_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data


async def test_submit_bug_report_with_page_url(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    resp = await _submit_report(client, token, page_url="/competitions/123")

    assert resp.status_code == 201
    assert resp.json()["page_url"] == "/competitions/123"


async def test_submit_bug_report_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    resp = await client.post(
        "/api/bug-reports",
        json={"title": "Something", "description": "Something broken here."},
    )
    assert resp.status_code == 401


async def test_submit_bug_report_title_too_short(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    resp = await _submit_report(client, token, title="Bug")  # < 5 chars

    assert resp.status_code == 422


async def test_submit_bug_report_description_too_short(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    resp = await _submit_report(client, token, description="short")  # < 10 chars

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/bug-reports/mine
# ---------------------------------------------------------------------------


async def test_get_my_reports_empty(client: AsyncClient, test_user: User, db_session: AsyncSession):
    token = await _login(client)
    resp = await client.get("/api/bug-reports/mine", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_my_reports_returns_own_only(
    client: AsyncClient, test_user: User, second_user: User, db_session: AsyncSession
):
    # test_user submits a report
    token1 = await _login(client)
    await _submit_report(client, token1)

    # second_user submits a report
    token2 = await _login(client, email="second@example.com")
    await _submit_report(client, token2)

    # test_user should only see their own
    resp = await client.get("/api/bug-reports/mine", headers={"Authorization": f"Bearer {token1}"})
    assert resp.status_code == 200
    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["user_id"] == str(test_user.id)


async def test_get_my_reports_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    resp = await client.get("/api/bug-reports/mine")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/bug-reports  (admin)
# ---------------------------------------------------------------------------


async def test_admin_list_all_reports(
    client: AsyncClient, test_user: User, second_user: User, db_session: AsyncSession
):
    # Both users submit a report
    token1 = await _login(client)
    await _submit_report(client, token1)

    token2 = await _login(client, email="second@example.com")
    await _submit_report(client, token2)

    # Promote test_user to admin and fetch all
    await _make_global_admin(db_session, test_user)
    token_admin = await _login(client)

    resp = await client.get("/api/bug-reports", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_non_admin_cannot_list_all_reports(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    resp = await client.get("/api/bug-reports", headers={"Authorization": f"Bearer {token}"})
    # Regular users get 403 from get_current_global_admin dep
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/bug-reports/{id}  (admin)
# ---------------------------------------------------------------------------


async def test_admin_update_status(client: AsyncClient, test_user: User, db_session: AsyncSession):
    token = await _login(client)
    create_resp = await _submit_report(client, token)
    report_id = create_resp.json()["id"]

    # Promote to admin
    await _make_global_admin(db_session, test_user)
    token_admin = await _login(client)

    resp = await client.patch(
        f"/api/bug-reports/{report_id}",
        json={"status": "in_review"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"


async def test_admin_update_status_not_found(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    import uuid

    await _make_global_admin(db_session, test_user)
    token = await _login(client)

    resp = await client.patch(
        f"/api/bug-reports/{uuid.uuid4()}",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_non_admin_cannot_update_status(
    client: AsyncClient, test_user: User, db_session: AsyncSession
):
    token = await _login(client)
    create_resp = await _submit_report(client, token)
    report_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/bug-reports/{report_id}",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
