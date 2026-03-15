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
    password: 'Password123!',
    confirmPassword: 'Password123!',
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
    fillForm({ confirmPassword: 'Different123!' })
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }))

    await waitFor(() => {
      // Both inline hint and form-level error show "Passwords do not match"
      expect(screen.getAllByText('Passwords do not match').length).toBeGreaterThan(0)
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('disables submit when password does not meet requirements', () => {
    renderRegister()
    fillForm({ password: 'short', confirmPassword: 'short' })

    expect(screen.getByRole('button', { name: /sign up/i })).toBeDisabled()
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
      expect(mockRegister).toHaveBeenCalledWith('bob@example.com', 'bob', 'Password123!')
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
