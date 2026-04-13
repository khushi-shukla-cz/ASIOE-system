import { BrowserRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DashboardPage from '@/pages/DashboardPage'
import { useStore } from '@/store/useStore'

vi.mock('@/components/dashboard/SkillProfileView', () => ({
  default: () => <div>Mock Skill Profile View</div>,
}))

vi.mock('@/components/dashboard/GapAnalysisView', () => ({
  default: () => <div>Mock Gap Analysis View</div>,
}))

vi.mock('@/components/dashboard/LearningPathView', () => ({
  default: () => <div>Mock Learning Path View</div>,
}))

vi.mock('@/components/graph/SkillGraphD3', () => ({
  default: () => <div>Mock Skill Graph View</div>,
}))

vi.mock('@/components/explainability/ExplainabilityConsole', () => ({
  default: () => <div>Mock Explainability Console</div>,
}))

vi.mock('@/components/dashboard/SimulationPanel', () => ({
  default: () => <div>Mock Simulation Panel</div>,
}))

const resultFixture = {
  session_id: 'session-1',
  status: 'completed',
  skill_profile: {
    skills: [
      {
        skill_id: 'python',
        name: 'Python',
      },
    ],
  },
  gap_analysis: {
    session_id: 'session-1',
    overall_readiness_score: 0.62,
    readiness_label: 'Near Ready',
    critical_gaps: [],
    major_gaps: [],
    minor_gaps: [],
    strength_areas: [],
    domain_coverage: [],
    reasoning_trace: 'trace',
    analysis_timestamp: '2026-04-14T00:00:00Z',
  },
  learning_path: {
    session_id: 'session-1',
    path_id: 'path-1',
    target_role: 'Backend Engineer',
    phases: [],
    total_modules: 3,
    total_hours: 12,
    total_weeks: 4,
    path_graph: {
      nodes: [{ id: 'n1', label: 'Python' }],
      edges: [],
    },
    efficiency_score: 0.9,
    redundancy_eliminated: 0,
    path_algorithm: 'topological_dfs',
    path_version: 1,
    reasoning_trace: 'trace',
    generated_at: '2026-04-14T00:00:00Z',
  },
  reasoning_trace: {
    session_id: 'session-1',
    parsing_trace: 'ok',
    normalization_trace: 'ok',
    gap_trace: 'ok',
    path_trace: 'ok',
    total_tokens_used: 100,
    model_used: 'test',
    generated_at: '2026-04-14T00:00:00Z',
  },
  processing_time_ms: 1200,
}

describe('DashboardPage', () => {
  beforeEach(() => {
    useStore.getState().reset()
  })

  it('renders empty state when no analysis result exists', () => {
    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    )

    expect(screen.getByText(/no analysis yet/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
  })

  it('supports tab navigation across dashboard views', async () => {
    const user = userEvent.setup()
    useStore.setState({
      sessionId: 'session-1',
      result: resultFixture as any,
    })

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    )

    expect(screen.getByRole('heading', { name: /skill profile/i })).toBeInTheDocument()
    expect(screen.getByText('Mock Skill Profile View')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /gap analysis/i }))
    expect(await screen.findByText('Mock Gap Analysis View')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /learning path/i }))
    expect(await screen.findByText('Mock Learning Path View')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /simulate/i }))
    expect(await screen.findByText('Mock Simulation Panel')).toBeInTheDocument()
  })
})
