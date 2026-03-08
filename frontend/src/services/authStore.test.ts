// authStore.test.ts
//
// These tests document the authStore contract that prevents two production bugs:
//
// BUG 1 — Perpetual loading screen for new users:
//   isInitializing was missing; without it, every page refresh started with
//   isAuthenticated: false, sending the user to /login even with valid cookies.
//   On slow networks, if the Dashboard's /competitions query hung, the isLoading
//   state never cleared → stuck spinner.
//
// BUG 2 — Flash of login page on refresh:
//   Same root cause. checkAuth was never called, so session cookies were ignored
//   after a hard refresh.

import { renderHook, act } from '@testing-library/react'
import { useAuthStore } from './authStore'

vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import api from './api'

// Zustand stores are module singletons — reset between tests to avoid leaks.
beforeEach(() => {
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    isInitializing: true,
  })
})

describe('authStore — initial state', () => {
  it('starts with isInitializing: true so routes are blocked until cookie is validated', () => {
    const { result } = renderHook(() => useAuthStore())
    expect(result.current.isInitializing).toBe(true)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })
})

describe('authStore — checkAuth', () => {
  it('valid cookie: sets isAuthenticated true and clears isInitializing', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.checkAuth()
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isInitializing).toBe(false)
    expect(result.current.user?.username).toBe('alice')
  })

  it('expired/missing cookie: clears auth and isInitializing so user reaches /login', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('401 Unauthorized'))

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.checkAuth()
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isInitializing).toBe(false)
    expect(result.current.user).toBeNull()
  })
})

describe('authStore — login/register clear isInitializing', () => {
  // If login/register complete before checkAuth (rare on fast connections),
  // isInitializing must still be cleared — otherwise the app stays on the
  // loading screen even after a successful login.

  it('login clears isInitializing', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        user: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
      },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.login('a@example.com', 'secret')
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isInitializing).toBe(false)
  })

  it('register clears isInitializing', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        user: { id: '2', username: 'bob', email: 'b@example.com', role: 'user', status: 'active' },
      },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.register('b@example.com', 'bob', 'secret')
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isInitializing).toBe(false)
  })
})
