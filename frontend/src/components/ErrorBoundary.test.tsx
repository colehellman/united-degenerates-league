// ErrorBoundary.test.tsx

import { render, screen, fireEvent } from '@testing-library/react'
import ErrorBoundary from './ErrorBoundary'

// Silence the expected console.error from React's error boundary reporting
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

// Component that throws on demand
function Bomb({ shouldThrow = false }: { shouldThrow?: boolean }) {
  if (shouldThrow) throw new Error('Kaboom')
  return <div>Safe content</div>
}

describe('ErrorBoundary — normal rendering', () => {
  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Safe content')).toBeInTheDocument()
  })
})

describe('ErrorBoundary — error caught', () => {
  it('renders the error UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <Bomb shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('shows error details in the expandable section', () => {
    render(
      <ErrorBoundary>
        <Bomb shouldThrow />
      </ErrorBoundary>,
    )
    // summary element triggers the details disclosure
    const summary = screen.getByText(/error details/i)
    expect(summary).toBeInTheDocument()
    // The error message is rendered inside the pre tag
    expect(screen.getByText(/Kaboom/)).toBeInTheDocument()
  })

  it('renders a custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback UI</div>}>
        <Bomb shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Custom fallback UI')).toBeInTheDocument()
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
  })
})

describe('ErrorBoundary — recovery', () => {
  it('renders children again after clicking Try Again', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <Bomb shouldThrow />
      </ErrorBoundary>,
    )

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    // Swap to a non-throwing child BEFORE resetting. If we reset first,
    // React immediately re-renders with the still-throwing child, which
    // re-triggers getDerivedStateFromError before the new child arrives.
    rerender(
      <ErrorBoundary>
        <Bomb shouldThrow={false} />
      </ErrorBoundary>,
    )

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(screen.getByText('Safe content')).toBeInTheDocument()
  })
})
