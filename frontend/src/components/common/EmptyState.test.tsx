import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Heart } from 'lucide-react'
import EmptyState from './EmptyState'

describe('EmptyState', () => {
  it('renders title', () => {
    render(
      <EmptyState
        icon={Heart}
        title="No items found"
      />
    )
    expect(screen.getByText('No items found')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(
      <EmptyState
        icon={Heart}
        title="No items"
        description="Try adjusting your filters"
      />
    )
    expect(screen.getByText('Try adjusting your filters')).toBeInTheDocument()
  })

  it('has role="status"', () => {
    const { container } = render(
      <EmptyState icon={Heart} title="Empty" />
    )
    expect(container.querySelector('[role="status"]')).toBeInTheDocument()
  })

  it('renders icon', () => {
    const { container } = render(
      <EmptyState icon={Heart} title="Empty" />
    )
    const icon = container.querySelector('.empty-state-icon svg')
    expect(icon).toBeInTheDocument()
  })

  it('renders action button and calls onClick', () => {
    const onAction = vi.fn()
    render(
      <EmptyState
        icon={Heart}
        title="Empty"
        action={{ label: 'Create new', onClick: onAction }}
      />
    )
    const actionBtn = screen.getByRole('button', { name: 'Create new' })
    fireEvent.click(actionBtn)
    expect(onAction).toHaveBeenCalled()
  })

  it('renders children when provided', () => {
    render(
      <EmptyState icon={Heart} title="Empty">
        <div>Custom content</div>
      </EmptyState>
    )
    expect(screen.getByText('Custom content')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <EmptyState
        icon={Heart}
        title="Empty"
        className="custom-class"
      />
    )
    const emptyState = container.querySelector('.empty-state')
    expect(emptyState).toHaveClass('custom-class')
  })

  it('renders button with primary variant by default', () => {
    render(
      <EmptyState
        icon={Heart}
        title="Empty"
        action={{ label: 'Action', onClick: () => {} }}
      />
    )
    const btn = screen.getByRole('button')
    expect(btn).toHaveClass('btn-primary')
  })

  it('renders button with secondary variant when specified', () => {
    render(
      <EmptyState
        icon={Heart}
        title="Empty"
        action={{ label: 'Action', onClick: () => {}, variant: 'secondary' }}
      />
    )
    const btn = screen.getByRole('button')
    expect(btn).toHaveClass('btn-secondary')
  })
})
