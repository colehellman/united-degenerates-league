// Register.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Register from './Register'
import { useAuthStore } from '../services/authStore'

const mockNavigate = vi.fn()
const mockRegister = vi.fn()

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderRegister() {
  vi.mocked(useAuthStore).mockReturnValue({ register: mockRegister } as any)
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  )
}

function fillForm(overrides: Record<string, string> = {}) {
  const defaults = {
    email: 'bob@example.com',
    username: 'bob',
    password: 'password123',
    confirmPassword: 'password123',
    ...overrides,
  }
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: defaults.email } })
  fireEvent.change(screen.getByLabelText(/username/i), { target: { value: defaults.username } })
  fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: defaults.password } })
  fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: defaults.confirmPassword } })
}

beforeEach(() => vi.clearAllMocks())

describe('Register — rendering', () => {
  it('renders all form fields', () => {
    renderRegister()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
  })
})

describe('Register — client-side validation', () => {
  it('shows error when passwords do not match', async () => {
    renderRegister()
    fillForm({ confirmPassword: 'different' })
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('shows error when password is shorter than 8 characters', async () => {
    renderRegister()
    fillForm({ password: 'short', confirmPassword: 'short' })
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument()
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })
})

describe('Register — successful submission', () => {
  it('calls register with correct args and navigates to /', async () => {
    mockRegister.mockResolvedValueOnce(undefined)
    renderRegister()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('bob@example.com', 'bob', 'password123')
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('shows loading text while submitting', async () => {
    mockRegister.mockReturnValue(new Promise(() => {}))
    renderRegister()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
  })
})

describe('Register — API errors', () => {
  it('displays server error on registration failure', async () => {
    mockRegister.mockRejectedValueOnce({
      response: { data: { detail: 'Email already in use' } },
    })
    renderRegister()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(screen.getByText('Email already in use')).toBeInTheDocument()
    })
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('displays generic fallback when response has no detail', async () => {
    mockRegister.mockRejectedValueOnce(new Error('Network error'))
    renderRegister()
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      expect(screen.getByText('Registration failed')).toBeInTheDocument()
    })
  })
})
