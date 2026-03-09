import { render, screen } from '@testing-library/react'
import Spinner from './Spinner'

describe('Spinner', () => {
  it('renders with role="status" and an accessible label', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument()
  })

  it('applies additional className when provided', () => {
    render(<Spinner className="py-2" />)
    expect(screen.getByRole('status')).toHaveClass('py-2')
  })
})
