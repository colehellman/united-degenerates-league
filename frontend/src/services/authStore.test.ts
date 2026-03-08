// authStore.test.ts
//
// Tests the authStore contract: session cookie validation, login,
// register, and logout. isInitializing was removed from the store
// (App.tsx now renders all routes without a loading guard); these
// tests cover only what the store actually provides.

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
  useAuthStore.setState({ user: null, isAuthenticated: false })
})

describe('authStore — initial state', () => {
  it('starts unauthenticated with no user', () => {
    const { result } = renderHook(() => useAuthStore())
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })
})

describe('authStore — checkAuth', () => {
  it('valid cookie: sets user and isAuthenticated true', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => { await result.current.checkAuth() })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.username).toBe('alice')
  })

  it('expired/missing cookie: leaves isAuthenticated false', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('401 Unauthorized'))

    const { result } = renderHook(() => useAuthStore())

    await act(async () => { await result.current.checkAuth() })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })
})

describe('authStore — login', () => {
  it('sets user and isAuthenticated on success', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        user: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
      },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => { await result.current.login('a@example.com', 'secret') })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.username).toBe('alice')
  })

  it('propagates errors so the Login page can display them', async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error('Invalid credentials'))

    const { result } = renderHook(() => useAuthStore())

    await expect(
      act(async () => { await result.current.login('a@example.com', 'wrong') })
    ).rejects.toThrow('Invalid credentials')

    expect(result.current.isAuthenticated).toBe(false)
  })
})

describe('authStore — register', () => {
  it('sets user and isAuthenticated on success', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        user: { id: '2', username: 'bob', email: 'b@example.com', role: 'user', status: 'active' },
      },
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => { await result.current.register('b@example.com', 'bob', 'secret') })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.username).toBe('bob')
  })
})

describe('authStore — logout', () => {
  it('clears user and isAuthenticated', async () => {
    useAuthStore.setState({
      user: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
      isAuthenticated: true,
    })

    vi.mocked(api.post).mockResolvedValueOnce({})

    const { result } = renderHook(() => useAuthStore())

    await act(async () => { await result.current.logout() })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('clears local state even if the logout API call fails (best-effort)', async () => {
    useAuthStore.setState({
      user: { id: '1', username: 'alice', email: 'a@example.com', role: 'user', status: 'active' },
      isAuthenticated: true,
    })

    vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useAuthStore())

    // Must NOT throw despite the API failure
    await act(async () => { await result.current.logout() })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })
})
