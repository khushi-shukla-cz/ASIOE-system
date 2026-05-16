import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import SkillGraphD3 from './SkillGraphD3'

const minimalGraph = {
  nodes: [
    {
      module_id: 'n1',
      label: 'Skill A',
      domain: 'technical',
      gap_severity: 'major',
      phase: 1,
      hours: 5,
    },
  ],
  edges: [],
}

describe('SkillGraphD3', () => {
  it('renders an svg and node elements for provided graph', async () => {
    const onNodeClick = vi.fn()
    const { container } = render(<div style={{ width: 800, height: 600 }}><SkillGraphD3 graph={minimalGraph as any} onNodeClick={onNodeClick} /></div>)

    // wait for svg to be present
    await waitFor(() => {
      expect(container.querySelector('svg')).toBeInTheDocument()
    })

    // nodes should be present (g.node)
    await waitFor(() => {
      const nodes = container.querySelectorAll('.node')
      expect(nodes.length).toBeGreaterThan(0)
    })
  })

  it('responds to keyboard activation on node', async () => {
    const onNodeClick = vi.fn()
    const { container } = render(<div style={{ width: 800, height: 600 }}><SkillGraphD3 graph={minimalGraph as any} onNodeClick={onNodeClick} /></div>)

    await waitFor(() => expect(container.querySelector('svg')).toBeInTheDocument())

    const node = container.querySelector('.node') as HTMLElement | null
    expect(node).not.toBeNull()
    if (!node) throw new Error('node not found')

    // simulate Enter key
    await userEvent.keyboard('{Tab}')
    node.focus()
    await userEvent.keyboard('{Enter}')

    // onNodeClick should be invoked
    await waitFor(() => expect(onNodeClick).toHaveBeenCalled())
  })
})
