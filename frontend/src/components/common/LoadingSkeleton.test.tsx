import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import LoadingSkeleton, {
  TextSkeleton,
  TextSkeletonSm,
  CircleSkeleton,
  CardSkeleton,
  ListSkeleton,
  GridSkeleton,
} from './LoadingSkeleton'

describe('LoadingSkeleton', () => {
  it('renders CardSkeleton by default', () => {
    const { container } = render(<LoadingSkeleton />)
    expect(container.querySelector('.skeleton-card')).toBeInTheDocument()
  })

  it('renders children when provided', () => {
    render(
      <LoadingSkeleton>
        <div>Custom content</div>
      </LoadingSkeleton>
    )
    expect(screen.getByText('Custom content')).toBeInTheDocument()
  })
})

describe('TextSkeleton', () => {
  it('renders with skeleton class', () => {
    const { container } = render(<TextSkeleton />)
    const skeleton = container.querySelector('.skeleton')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('h-4', 'w-full')
  })

  it('accepts custom className', () => {
    const { container } = render(<TextSkeleton className="custom-class" />)
    const skeleton = container.querySelector('.skeleton')
    expect(skeleton).toHaveClass('custom-class')
  })
})

describe('TextSkeletonSm', () => {
  it('renders smaller text skeleton', () => {
    const { container } = render(<TextSkeletonSm />)
    const skeleton = container.querySelector('.skeleton')
    expect(skeleton).toHaveClass('h-3', 'w-3/4')
  })
})

describe('CircleSkeleton', () => {
  it('renders circular skeleton with default size', () => {
    const { container } = render(<CircleSkeleton />)
    const skeleton = container.querySelector('.skeleton')
    expect(skeleton).toHaveClass('rounded-full', 'animate-pulse')
    expect(skeleton).toHaveStyle({ width: '40px', height: '40px' })
  })

  it('accepts custom size', () => {
    const { container } = render(<CircleSkeleton size={64} />)
    const skeleton = container.querySelector('.skeleton')
    expect(skeleton).toHaveStyle({ width: '64px', height: '64px' })
  })
})

describe('CardSkeleton', () => {
  it('renders card skeleton structure', () => {
    const { container } = render(<CardSkeleton />)
    const card = container.querySelector('.skeleton-card')
    expect(card).toBeInTheDocument()
    const skeletons = card?.querySelectorAll('.skeleton')
    expect(skeletons).toHaveLength(4)
  })
})

describe('ListSkeleton', () => {
  it('renders with default count of 5 items', () => {
    const { container } = render(<ListSkeleton />)
    const items = container.querySelectorAll('.flex.items-center.gap-3')
    expect(items).toHaveLength(5)
  })

  it('renders with custom count', () => {
    const { container } = render(<ListSkeleton count={3} />)
    const items = container.querySelectorAll('.flex.items-center.gap-3')
    expect(items).toHaveLength(3)
  })
})

describe('GridSkeleton', () => {
  it('renders with default count and columns', () => {
    const { container } = render(<GridSkeleton />)
    const cards = container.querySelectorAll('.skeleton-card')
    expect(cards).toHaveLength(6)
  })

  it('renders with custom count and columns', () => {
    const { container } = render(<GridSkeleton count={4} columns={2} />)
    const cards = container.querySelectorAll('.skeleton-card')
    expect(cards).toHaveLength(4)
  })
})
