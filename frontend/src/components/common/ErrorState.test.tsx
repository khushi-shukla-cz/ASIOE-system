import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ErrorState from './ErrorState'

describe('ErrorState', () => {
  it('renders title and message', () => {
    render(
      <ErrorState
        type="error"
        title="Test Error"
        message="This is a test error message"
      />
    )
    expect(screen.getByText('Test Error')).toBeInTheDocument()
    expect(screen.getByText('This is a test error message')).toBeInTheDocument()
  })

  it('has role="alert" for accessibility', () => {
    const { container } = render(
      <ErrorState type="error" title="Test" />
    )
    expect(container.querySelector('[role="alert"]')).toBeInTheDocument()
  })

  it('has aria-live="polite"', () => {
    const { container } = render(
      <ErrorState type="error" title="Test" />
    )
    const alert = container.querySelector('[role="alert"]')
    expect(alert).toHaveAttribute('aria-live', 'polite')
  })

  describe('types', () => {
    it('renders error type with correct styling', () => {
      const { container } = render(
        <ErrorState type="error" title="Error" />
      )
      const alert = container.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-rose-50')
    })

    it('renders warning type with correct styling', () => {
      const { container } = render(
        <ErrorState type="warning" title="Warning" />
      )
      const alert = container.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-amber-50')
    })

    it('renders info type with correct styling', () => {
      const { container } = render(
        <ErrorState type="info" title="Info" />
      )
      const alert = container.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-sky-50')
    })

    it('renders success type with correct styling', () => {
      const { container } = render(
        <ErrorState type="success" title="Success" />
      )
      const alert = container.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-sage-50')
    })
  })

  it('renders dismiss button when onDismiss provided', () => {
    const onDismiss = vi.fn()
    render(
      <ErrorState
        type="error"
        title="Test"
        onDismiss={onDismiss}
      />
    )
    const dismissBtn = screen.getByLabelText('Dismiss')
    expect(dismissBtn).toBeInTheDocument()
    fireEvent.click(dismissBtn)
    expect(onDismiss).toHaveBeenCalled()
  })

  it('renders action button and calls onClick', () => {
    const onAction = vi.fn()
    render(
      <ErrorState
        type="error"
        title="Test"
        action={{ label: 'Retry', onClick: onAction }}
      />
    )
    const actionBtn = screen.getByRole('button', { name: 'Retry' })
    fireEvent.click(actionBtn)
    expect(onAction).toHaveBeenCalled()
  })

  it('renders children when provided', () => {
    render(
      <ErrorState type="error" title="Test">
        <div>Custom children content</div>
      </ErrorState>
    )
    expect(screen.getByText('Custom children content')).toBeInTheDocument()
  })

  it('defaults to error type', () => {
    const { container } = render(<ErrorState title="Test" />)
    const alert = container.querySelector('[role="alert"]')
    expect(alert).toHaveClass('bg-rose-50')
  })
})
