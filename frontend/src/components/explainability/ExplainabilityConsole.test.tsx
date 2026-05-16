import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ExplainabilityConsole from './ExplainabilityConsole'

const mockTrace = {
  model_used: 'llama-70b',
  total_tokens_used: 12345,
  parsing_trace: 'parsed resume and jd',
  normalization_trace: 'normalized tokens',
  gap_trace: 'computed gaps',
  path_trace: 'built path',
}

const mockPath = {
  total_modules: 2,
  efficiency_score: 0.8,
  phases: [
    {
      phase_id: 'p1',
      modules: [
        {
          module_id: 'm1',
          skill_name: 'React Basics',
          domain: 'technical',
          sequence_order: 1,
          difficulty_level: 'beginner',
          estimated_hours: 4,
          why_selected: 'Covers fundamentals',
          dependency_chain: [],
        },
      ],
    },
    {
      phase_id: 'p2',
      modules: [
        {
          module_id: 'm2',
          skill_name: 'Advanced State',
          domain: 'technical',
          sequence_order: 2,
          difficulty_level: 'intermediate',
          estimated_hours: 6,
          why_selected: 'Deep dive into state management',
          dependency_chain: ['React Basics'],
        },
      ],
    },
  ],
}

describe('ExplainabilityConsole', () => {
  it('renders engine trace headers and module list', () => {
    render(<ExplainabilityConsole trace={mockTrace as any} path={mockPath as any} />)

    expect(screen.getByText(/Engine Reasoning Traces/i)).toBeInTheDocument()
    expect(screen.getByText(/Module-Level Explanations/i)).toBeInTheDocument()

    // Modules list should contain items
    expect(screen.getByRole('listbox', { name: /Module list/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/React Basics/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Advanced State/)).toBeInTheDocument()
  })

  it('filters modules via search input', async () => {
    render(<ExplainabilityConsole trace={mockTrace as any} path={mockPath as any} />)
    const input = screen.getByPlaceholderText(/Search skills.../i)
    expect(input).toBeInTheDocument()

    // type into search to filter
    fireEvent.change(input, { target: { value: 'Advanced' } })
    expect(screen.queryByLabelText(/React Basics/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Advanced State/)).toBeInTheDocument()
  })

  it('shows module details when selected', () => {
    render(<ExplainabilityConsole trace={mockTrace as any} path={mockPath as any} />)
    const moduleBtn = screen.getByLabelText(/React Basics/)
    fireEvent.click(moduleBtn)

    // detail region should appear
    expect(screen.getByRole('region', { name: /Details for React Basics/i })).toBeInTheDocument()
    expect(screen.getByText(/Covers fundamentals/i)).toBeInTheDocument()
  })
})
