// Login.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Login from './Login'
import { useAuthStore } from '../services/authStore'

const mockNavigate = vi.fn()
const mockLogin = vi.fn()

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderLogin(initialPath = '/login') {
  vi.mocked(useAuthStore).mockReturnValue({
    login: mockLogin,
  } as any)
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Login />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Login — rendering', () => {
  it('renders email, password fields and submit button', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders a link to the register page', () => {
    renderLogin()
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument()
  })
})

describe('Login — successful submission', () => {
  it('calls login with entered credentials and navigates to /', async () => {
    mockLogin.mockResolvedValueOnce(undefined)
    renderLogin()

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'hunter2' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('alice@example.com', 'hunter2')
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('shows loading text while submitting', async () => {
    // Never resolves so we can observe the loading state
    mockLogin.mockReturnValue(new Promise(() => {}))
    renderLogin()

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'hunter2' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })
})

describe('Login — redirect after login', () => {
  it('navigates to redirect param after successful login', async () => {
    mockLogin.mockResolvedValueOnce(undefined)
    renderLogin('/login?redirect=/invite/abc123')

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'hunter2' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/invite/abc123')
    })
  })
})

describe('Login — failed submission', () => {
  it('displays server error message on login failure', async () => {
    mockLogin.mockRejectedValueOnce({
      response: { data: { detail: 'Invalid credentials' } },
    })
    renderLogin()

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'alice@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('displays generic fallback when response has no detail', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Network error'))
    renderLogin()

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Login failed')).toBeInTheDocument()
    })
  })
})
