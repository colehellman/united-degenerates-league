import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Warn when the built-in API URL points to localhost but the site is served
// from a remote host — this almost always means VITE_API_URL was not set at
// build time.  The warning only fires once and only in the browser console.
if (
  API_URL.includes('localhost') &&
  typeof window !== 'undefined' &&
  !window.location.hostname.includes('localhost') &&
  !window.location.hostname.includes('127.0.0.1')
) {
  console.error(
    '[UDL] VITE_API_URL was not set at build time — API calls will fail.\n' +
    `Current API target: ${API_URL}\n` +
    'Set VITE_API_URL in your Render environment variables and redeploy the frontend.'
  )
}

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  // Send httpOnly cookies on every request
  withCredentials: true,
  // 15s timeout prevents cold-start hangs (Render free tier wakes in ~30-60s on
  // first hit, but we'd rather fail fast than leave stale refresh requests
  // in-flight while the user fills in the login form).
  timeout: 15000,
})

// Extend axios config to support per-request toast suppression.
// Callers that handle their own error UI pass _skipToast: true to avoid
// double-toasting (e.g. inline form validation messages).
// Both interfaces must be augmented: AxiosRequestConfig is what callers pass
// to api.get/post; InternalAxiosRequestConfig is what interceptors receive.
declare module 'axios' {
  interface AxiosRequestConfig {
    _skipToast?: boolean
    _retry?: boolean
  }
  interface InternalAxiosRequestConfig {
    _skipToast?: boolean
    _retry?: boolean
  }
}

// Track whether a refresh is already in-flight to avoid infinite loops
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

// Single-shot flag: set by authStore.login/register so that when a background
// checkAuth refresh fails AFTER a successful login (race condition), we don't
// hard-redirect the user back to /login.  Consumed immediately after read.
// Most visible on mobile/slow networks where the cold-start wake-up means the
// refresh request is still in-flight for 15+ seconds while the user logs in.
let _suppressNextRefreshRedirect = false

export function suppressRefreshRedirect(): void {
  _suppressNextRefreshRedirect = true
}

// In-memory access token. Injected as Authorization: Bearer on every request
// so the app works regardless of cross-origin cookie restrictions (mobile Safari
// ITP blocks SameSite=None cookies from onrender.com subdomains).  Storing it
// in memory (not localStorage) means XSS cannot exfiltrate it, and it is
// cleared on page reload — the httpOnly refresh cookie or localStorage token
// then issues a new one.
let _accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  _accessToken = token
}

// Refresh token in localStorage.  localStorage persists across page reloads,
// tab closes, AND iOS tab suspension — which is the critical difference from
// sessionStorage.  On iOS, when the OS kills a browser tab to reclaim memory
// and the user returns to it, the browser starts a NEW session (sessionStorage
// is cleared).  localStorage is NOT cleared on session boundaries, matching
// the 7-day refresh token TTL.  It is still explicitly cleared on logout.
// Never accessible cross-origin — safe fallback for mobile Safari where ITP
// blocks the httpOnly refresh cookie from onrender.com subdomains.
const RT_KEY = 'rt'

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(RT_KEY, token)
  } else {
    localStorage.removeItem(RT_KEY)
  }
}

// Inject Bearer token on every outbound request when we have one in memory.
api.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  return config
})

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

// Handle auth errors with automatic token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig

    // Show error message for non-auth errors, unless the caller opted out.
    // Callers that render inline error messages pass _skipToast: true to avoid
    // surfacing the same error twice.
    if (error.response?.status !== 401 && !originalRequest._skipToast) {
      let message = error.response?.data?.detail || 'An unexpected error occurred'

      // Network errors (no response at all) usually mean the API URL is wrong
      // or the backend is down.  Give a more actionable message.
      if (!error.response && (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED')) {
        message = 'Cannot reach the server. It may be starting up — please try again in a moment.'
      }

      toast.error(message)
    }

    // Skip the auto-refresh cycle for auth endpoints that don't need a session:
    //   /auth/refresh — if this itself returns 401, retrying would loop forever
    //   /auth/login   — a 401 here means wrong credentials; attempting to refresh
    //                   would forward the *refresh* error ("No refresh token
    //                   provided") to the UI instead of "Incorrect password"
    //   /auth/register — same reasoning as login
    const AUTH_ENDPOINTS = ['/auth/refresh', '/auth/login', '/auth/register']
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !AUTH_ENDPOINTS.includes(originalRequest.url ?? '')
    ) {
      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve) => {
          addRefreshSubscriber((_token: string) => {
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Attempt refresh — httpOnly refresh cookie sent automatically when
        // available.  On mobile Safari (ITP blocks cross-origin cookies), pass
        // the localStorage token in the request body as a fallback; the
        // backend prefers body over cookie when both are present.
        const storedRefreshToken = localStorage.getItem(RT_KEY) || undefined
        const res = await api.post(
          '/auth/refresh',
          storedRefreshToken ? { refresh_token: storedRefreshToken } : {},
          {
            // Render free-tier cold starts take 30-60s — well above the global
            // 15s timeout.  Override here so a valid localStorage refresh token
            // isn't abandoned mid-wake and the user is forced to re-login.
            timeout: 60000,
            // Refresh failures are handled via redirect logic below; suppress the
            // generic "An unexpected error occurred" toast so it doesn't fire on
            // every cold-start page load before the backend is warm.
            _skipToast: true,
          },
        )
        setAccessToken(res.data.access_token)
        // Rotate the stored refresh token so the next page reload can still
        // issue a fresh access token without re-login.
        if (res.data.refresh_token) {
          localStorage.setItem(RT_KEY, res.data.refresh_token)
        }
        onTokenRefreshed(res.data.access_token)
        return api(originalRequest)
      } catch (refreshError: any) {
        // Refresh failed — clear the in-memory access token unconditionally.
        setAccessToken(null)
        // Only wipe the stored refresh token when the server explicitly rejects
        // it (HTTP 401 = invalid or expired token).  Network errors, timeouts
        // (axios code ECONNABORTED / ERR_NETWORK), and 5xx responses do NOT
        // mean the token is bad — Render free-tier cold starts routinely cause
        // 15 s timeouts.  Clearing on those would destroy a valid token and
        // force the user to re-login every morning.
        if (refreshError?.response?.status === 401) {
          localStorage.removeItem(RT_KEY)
        }
        // Only hard-redirect to /login for mid-session expiry (user is on a
        // protected page). For the initial auth check, let the error propagate
        // so checkAuth()'s catch sets isInitializing=false and React Router's
        // <Navigate> handles the redirect client-side.
        // Using window.location on /login or /register causes a full-page reload
        // loop: /login loads → checkAuth → 401 → refresh → 401 → redirect → repeat.
        //
        // _suppressNextRefreshRedirect handles the race condition where login()
        // succeeds and navigate('/') fires while a checkAuth-triggered refresh is
        // still in-flight.  Without this guard the stale refresh failure would
        // kick the freshly-logged-in user back to /login.  Most visible on mobile
        // networks and after Render cold-starts.
        const shouldRedirect = !_suppressNextRefreshRedirect
        _suppressNextRefreshRedirect = false // consume the one-shot flag
        if (
          shouldRedirect &&
          window.location.pathname !== '/login' &&
          window.location.pathname !== '/register'
        ) {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default api
