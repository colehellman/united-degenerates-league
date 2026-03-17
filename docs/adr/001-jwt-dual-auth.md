# ADR-001: JWT Dual Authentication (Cookies + Bearer)

**Status:** Accepted
**Date:** 2025-12-15

## Context

The app needs authentication that works on desktop browsers and mobile Safari. Mobile Safari's Intelligent Tracking Prevention (ITP) blocks cross-origin `SameSite=None` cookies from `*.onrender.com` subdomains, which breaks httpOnly cookie-based auth for the deployed app.

## Decision

Use a dual-mode authentication strategy:

1. **httpOnly cookies** — set on login/register responses with `SameSite=Lax` (dev) or `SameSite=None; Secure` (prod). The backend checks cookies first.
2. **Bearer header** — the frontend stores the access token in memory and injects it via an Axios request interceptor. This works regardless of cookie policy.
3. **Refresh token fallback** — stored in `localStorage` so it persists across iOS tab suspension. On 401, the frontend attempts a refresh using the stored token in the request body (not relying on cookies).

The backend's `get_current_user` dependency checks Bearer header first, then falls back to cookies.

## Consequences

**Positive:**
- Auth works on all browsers including mobile Safari with ITP
- Access token in memory (not localStorage) limits XSS exposure
- httpOnly cookies still protect users on browsers that support them

**Negative:**
- Dual-check logic in `core/deps.py` is more complex than cookie-only or token-only
- Refresh token in localStorage is accessible to XSS (mitigated by short TTL and rotation)
