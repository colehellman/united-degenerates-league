// BugReportModal.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BugReportModal from './BugReportModal'
import api from '../services/api'
import toast from 'react-hot-toast'

vi.mock('../services/api', () => ({
  default: { post: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

function renderModal(isOpen: boolean, onClose = vi.fn()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return { onClose, ...render(
    <QueryClientProvider client={qc}>
      <BugReportModal isOpen={isOpen} onClose={onClose} />
    </QueryClientProvider>,
  )}
}

beforeEach(() => vi.clearAllMocks())

describe('BugReportModal — visibility', () => {
  it('renders nothing when isOpen is false', () => {
    renderModal(false)
    expect(screen.queryByText('Report a Bug')).not.toBeInTheDocument()
  })

  it('renders the form when isOpen is true', () => {
    renderModal(true)
    expect(screen.getByText('Report a Bug')).toBeInTheDocument()
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
  })

  it('renders all category options', () => {
    renderModal(true)
    const select = screen.getByLabelText(/category/i) as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toContain('ui')
    expect(options).toContain('performance')
    expect(options).toContain('data')
    expect(options).toContain('auth')
    expect(options).toContain('other')
  })
})

describe('BugReportModal — character count', () => {
  it('updates character count as user types in description', () => {
    renderModal(true)
    const textarea = screen.getByLabelText(/description/i)
    fireEvent.change(textarea, { target: { value: 'hello world' } })
    expect(screen.getByText('11/2000')).toBeInTheDocument()
  })
})

describe('BugReportModal — successful submission', () => {
  it('posts to /bug-reports with form data', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: '1' } })
    renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Button is broken' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Click submit and nothing happens' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/bug-reports', expect.objectContaining({
        title: 'Button is broken',
        description: 'Click submit and nothing happens',
        category: 'other',
      }))
    })
  })

  it('shows success toast and calls onClose on success', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: '1' } })
    const { onClose } = renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'A bug title here' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Detailed description text' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled()
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('disables submit button while pending', async () => {
    vi.mocked(api.post).mockReturnValue(new Promise(() => {}))
    renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Loading bug' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Something goes wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled()
  })
})

describe('BugReportModal — error handling', () => {
  it('displays a string error from the API', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { data: { detail: 'Title is too short' } },
    })
    renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Bug' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Bad thing happened' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => {
      expect(screen.getByText('Title is too short')).toBeInTheDocument()
    })
  })

  it('joins array-format validation errors from the API', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { data: { detail: [{ msg: 'field required' }, { msg: 'too short' }] } },
    })
    renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Test bug' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Some description' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => {
      expect(screen.getByText('field required; too short')).toBeInTheDocument()
    })
  })

  it('falls back to err.message when response detail is absent', async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))
    renderModal(true)

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Network bug' } })
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Connection dropped' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })
})

describe('BugReportModal — cancel / close', () => {
  it('calls onClose when Cancel is clicked', () => {
    const { onClose } = renderModal(true)
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('resets form fields when closed via cancel', async () => {
    const onClose = vi.fn()
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const { rerender } = render(
      <QueryClientProvider client={qc}>
        <BugReportModal isOpen={true} onClose={onClose} />
      </QueryClientProvider>,
    )

    // Type something then cancel
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Typed title' } })
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    // Reopen — form should be cleared
    rerender(
      <QueryClientProvider client={qc}>
        <BugReportModal isOpen={true} onClose={onClose} />
      </QueryClientProvider>,
    )
    expect((screen.getByLabelText(/title/i) as HTMLInputElement).value).toBe('')
  })
})
