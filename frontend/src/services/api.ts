import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  // Send httpOnly cookies on every request
  withCredentials: true,
})

// Extend axios config to support per-request toast suppression.
// Callers that handle their own error UI pass _skipToast: true to avoid
// double-toasting (e.g. inline form validation messages).
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _skipToast?: boolean
    _retry?: boolean
  }
}

// Track whether a refresh is already in-flight to avoid infinite loops
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

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
      toast.error(error.response?.data?.detail || 'An unexpected error occurred')
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
        // Attempt refresh — cookie is sent automatically
        const res = await api.post('/auth/refresh')
        onTokenRefreshed(res.data.access_token)
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed. Only hard-redirect to /login for mid-session expiry
        // (user is on a protected page). For the initial auth check, let the
        // error propagate so checkAuth()'s catch sets isInitializing=false and
        // React Router's <Navigate> handles the redirect client-side.
        // Using window.location on /login or /register causes a full-page reload
        // loop: /login loads → checkAuth → 401 → refresh → 401 → redirect → repeat.
        if (
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
