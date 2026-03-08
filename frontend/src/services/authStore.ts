import { create } from 'zustand'
import api from './api'

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
    // Tokens are set as httpOnly cookies by the backend.
    set({ user: response.data.user, isAuthenticated: true, isInitializing: false })
  },

  register: async (email, username, password) => {
    const response = await api.post('/auth/register', { email, username, password })
    set({ user: response.data.user, isAuthenticated: true, isInitializing: false })
  },

  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Best-effort — even if the call fails, clear local state
    }
    set({ user: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    try {
      // Cookie is sent automatically — if valid, we get user data back
      const response = await api.get('/users/me')
      set({ user: response.data, isAuthenticated: true, isInitializing: false })
    } catch {
      set({ user: null, isAuthenticated: false, isInitializing: false })
    }
  },
}))
