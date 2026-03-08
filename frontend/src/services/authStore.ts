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
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password })
    // Tokens are now set as httpOnly cookies by the backend.
    // We only use the response body for the user object.
    set({ user: response.data.user, isAuthenticated: true })
  },

  register: async (email, username, password) => {
    const response = await api.post('/auth/register', { email, username, password })
    set({ user: response.data.user, isAuthenticated: true })
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
      set({ user: response.data, isAuthenticated: true })
    } catch {
      set({ user: null, isAuthenticated: false })
    }
  },
}))
