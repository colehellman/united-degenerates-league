import { create } from 'zustand'
import api, { suppressRefreshRedirect, setAccessToken, setRefreshToken } from './api'

interface User {
  id: string
  email: string
  username: string
  role: string
  status: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  // True until the first checkAuth completes. Prevents routing decisions based
  // on the initial isAuthenticated: false before the cookie is validated.
  isInitializing: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isInitializing: true,

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password })
    // Store tokens so they survive page reloads on mobile Safari where ITP
    // blocks cross-origin SameSite=None cookies from onrender.com subdomains.
    // access_token → module memory (Bearer header injection via interceptor)
    // refresh_token → localStorage (persists across iOS tab kills/restores)
    setAccessToken(response.data.access_token)
    setRefreshToken(response.data.refresh_token)
    // Suppress any redirect that a concurrent checkAuth refresh might trigger —
    // if checkAuth was in-flight when login succeeded, its refresh failure would
    // otherwise hard-redirect the freshly-logged-in user back to /login.
    suppressRefreshRedirect()
    set({ user: response.data.user, isAuthenticated: true, isInitializing: false })
  },

  register: async (email, username, password) => {
    const response = await api.post('/auth/register', { email, username, password })
    setAccessToken(response.data.access_token)
    setRefreshToken(response.data.refresh_token)
    suppressRefreshRedirect()
    set({ user: response.data.user, isAuthenticated: true, isInitializing: false })
  },

  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Best-effort — even if the call fails, clear local state
    }
    setAccessToken(null)
    setRefreshToken(null)
    set({ user: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    // Suppress hard redirect for the initial auth check — if the refresh cookie
    // is missing (mobile Safari ITP) and the localStorage token is also gone,
    // let React Router's <Navigate> handle the redirect client-side instead of
    // doing a full-page reload that destroys all module state and causes a loop.
    suppressRefreshRedirect()
    try {
      // Cookie is sent automatically — if valid, we get user data back.
      // timeout: 60000 — Render free-tier cold starts take 30-60s.  With the
      // global 15s timeout, a sleeping backend causes /users/me to time out
      // (not 401), so the response interceptor never enters the refresh cycle
      // and the user is kicked to /login.  A 60s window lets Render wake the
      // backend in time to return 401, which then triggers the refresh flow
      // and keeps the user logged in.
      // _skipToast: true — timeout errors have no error.response, so the
      // interceptor's 401 guard doesn't protect them from the generic toast.
      const response = await api.get('/users/me', { timeout: 60000, _skipToast: true })
      set({ user: response.data, isAuthenticated: true, isInitializing: false })
    } catch {
      set({ user: null, isAuthenticated: false, isInitializing: false })
    }
  },
}))
