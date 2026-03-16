# Invite Links for Competitions

## Summary

Allow competition participants to share invite links that let anyone (existing or new users) join a competition. Admin-generated links (created by users in `league_admin_ids` or global admins) bypass the `requires_approval` join type; participant-generated links follow the normal join flow.

## Data Model

New `InviteLink` table:

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | Standard |
| `competition_id` | UUID FK → Competition | Cascade delete |
| `created_by_user_id` | UUID FK → User | Who generated the link |
| `token` | String, unique, indexed | 12-char URL-safe random string (`secrets.token_urlsafe(9)`). Unique constraint handles the astronomically unlikely collision — retry on IntegrityError. |
| `is_admin_invite` | Boolean | True if creator was in `league_admin_ids` or was a global admin at creation time |
| `use_count` | Integer, default 0 | Incremented on each successful join or join request via this link |
| `created_at` | DateTime, default utcnow | Standard |
| `updated_at` | DateTime, onupdate utcnow | Standard, consistent with other models |

**Lifecycle:** Links are valid as long as the competition status is not `COMPLETED`. Users can join via invite link when competition is `UPCOMING` or `ACTIVE`. No explicit expiration. No per-link usage limit — anyone with the link can join (up to `max_participants`).

**Relationships:** Competition has many InviteLinks. User has many InviteLinks. Cascade delete with competition.

## API Endpoints

### Create invite link

`POST /api/competitions/{competition_id}/invite-links`

- **Auth:** Required. Must be a participant.
- **Logic:** Creates an InviteLink. Sets `is_admin_invite = True` if the user is in `competition.league_admin_ids` or `current_user.role == UserRole.GLOBAL_ADMIN`.
- **Response:** `{ id, token, is_admin_invite, use_count, created_at, invite_url }`
- **`invite_url` construction:** The frontend constructs the full URL from the token (e.g., `${window.location.origin}/invite/${token}`). The backend response only includes `token`; the frontend builds the shareable URL.

### List invite links

`GET /api/competitions/{competition_id}/invite-links`

- **Auth:** Required. Must be a participant.
- **Logic:** Returns links created by the current user. Admins see all links for the competition.
- **Response:** Array of invite link objects.

### Resolve invite token

`GET /api/invite/{token}`

- **Auth:** Optional (unauthenticated access allowed).
- **Router:** Registered as a separate router in `main.py` with prefix `/api/invite` (not under the `/api/competitions` prefix).
- **Logic:** Looks up the token, joins Competition and League tables, checks competition is not COMPLETED, returns limited competition info.
- **Response:** `{ competition_id, competition_name, description, league_display_name (from League.display_name), mode, status, participant_count, max_participants, is_admin_invite }`
- **Errors:** 404 if token not found. 410 if competition is completed.

### Join via invite (modification to existing endpoint)

`POST /api/competitions/{competition_id}/join`

- **Change:** Accept optional request body with `invite_token` field. New schema: `JoinCompetitionRequest(BaseModel)` with `invite_token: Optional[str] = None`. The endpoint parameter uses `Body(default=None)` so callers can omit the body entirely for backward compatibility.
- **Add status guard:** Reject joins when competition status is `COMPLETED` (currently missing from the endpoint).
- **Logic:**
  - If `invite_token` is provided, validate it belongs to this competition and competition is not completed.
  - If `is_admin_invite` is true AND competition `join_type` is `requires_approval`, bypass approval and create Participant directly.
  - If `is_admin_invite` is false, follow normal flow (immediate for open, join request for requires_approval).
  - Increment `use_count` atomically (`UPDATE invite_links SET use_count = use_count + 1`) on any usage (join or join request).
  - Check for existing pending JoinRequest before creating a duplicate — return appropriate message if one already exists.
- **Existing behavior unchanged** when no invite_token is provided.

## Frontend

### New route: `/invite/{token}`

An invite landing page that:

1. Calls `GET /api/invite/{token}` on mount.
2. **Logged-in user:** Shows competition info (name, description, league, mode, participant count) and a "Join Competition" button. On click, calls `POST /api/competitions/{id}/join` with `invite_token`. On success, redirects to `/competitions/{id}`.
3. **Not logged in:** Shows the same competition info. Button says "Sign Up to Join" and redirects to `/register?redirect=/invite/{token}`. After auth, user returns to the invite page.
4. **Error states:** Invalid token → "This invite link is invalid." Completed competition → "This competition has already ended." Already a participant → message + link to competition detail.

**Routing note:** The `/invite/:token` route must be placed **outside** the authenticated `<Layout />` wrapper in `App.tsx`, similar to `/login` and `/register`, so unauthenticated users can access it.

### Competition detail page — sharing section

Visible to all participants, rendered as a card/section near the header area:

- Heading: "Invite Friends"
- Helper text: "Copy this link to invite friends. They can join even if they don't have an account yet."
- On first visit: "Generate Invite Link" button → calls POST, displays result with copy-to-clipboard.
- On subsequent visits: Fetches user's links via GET, shows most recent link with copy-to-clipboard button. "Generate New Link" option available but not prominent.
- No admin-specific UI — admin status is determined automatically by the backend.

### Redirect after auth

The `/register` and `/login` pages need to support a `redirect` query parameter. After successful auth, navigate to the redirect URL instead of the default dashboard. The authenticated route guards in `App.tsx` (`isAuthenticated ? <Navigate to="/" />`) must also respect the `redirect` param to avoid overriding it.

## Edge Cases

- **Invalid token:** 404 from resolve endpoint. Frontend shows error message.
- **Completed competition:** 410 from resolve endpoint. Frontend shows "competition has ended."
- **UPCOMING competition:** Invite links work — users can join before a competition starts.
- **Already a participant:** Existing join endpoint logic handles this. Frontend shows message + link to competition.
- **Max participants reached:** Existing join endpoint logic handles this. Invite link doesn't override capacity.
- **Duplicate join request:** Before creating a JoinRequest, check for existing pending request for same user+competition. Return "You already have a pending join request" instead of creating a duplicate.
- **Multiple links per user:** Allowed. UI shows most recent by default.
- **Private competitions:** Resolve endpoint returns limited info only (name, description, participant count). No game/leaderboard data exposed.
- **Competition deleted:** Cascade delete removes all invite links.
- **Race condition on use_count:** Use atomic SQL increment (`use_count = InviteLink.use_count + 1`) to avoid lost updates.
- **Token collision:** Unique constraint on `token` column handles this. Retry with new token on IntegrityError (extremely unlikely with 72 bits of entropy).

## Out of Scope

- **Link revocation/deletion:** Not included in v1. The only way a link becomes invalid is when the competition completes or is deleted. Can be added later if needed.

## Migration

Single Alembic migration adding the `invite_links` table.

## Files to Create/Modify

### New files
- `backend/app/models/invite_link.py` — InviteLink model
- `backend/app/schemas/invite_link.py` — Pydantic schemas (InviteLinkResponse, InviteResolveResponse)
- `backend/app/api/invite.py` — Invite resolve router (separate from competitions router)
- `backend/alembic/versions/xxx_add_invite_links.py` — Migration
- `frontend/src/pages/InviteLanding.tsx` — Invite landing page

### Modified files
- `backend/app/models/__init__.py` — Export InviteLink
- `backend/app/main.py` — Register invite router
- `backend/app/api/competitions.py` — Add invite link CRUD endpoints, modify join endpoint
- `backend/app/schemas/participant.py` — Add `JoinCompetitionRequest` schema with optional `invite_token`
- `frontend/src/pages/CompetitionDetail.tsx` — Add invite sharing section
- `frontend/src/services/api.ts` — Add invite link API calls
- `frontend/src/App.tsx` — Add `/invite/:token` route outside auth guards, update auth redirect logic
- `frontend/src/pages/Login.tsx` — Support `redirect` query param
- `frontend/src/pages/Register.tsx` — Support `redirect` query param
