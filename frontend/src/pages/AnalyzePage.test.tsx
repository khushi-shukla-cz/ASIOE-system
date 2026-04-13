import { BrowserRouter } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AnalyzePage from '@/pages/AnalyzePage'
import { runAnalysis } from '@/utils/api'

vi.mock('@/utils/api', () => ({
  runAnalysis: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('AnalyzePage', () => {
  it('keeps submit disabled when required inputs are missing', async () => {
    render(
      <BrowserRouter>
        <AnalyzePage />
      </BrowserRouter>
    )

    const submitBtn = screen.getByRole('button', { name: /run adaptive analysis/i })
    expect(submitBtn).toBeDisabled()
    expect(screen.getByText(/upload a resume to continue/i)).toBeInTheDocument()
  })

  it('enables submit only when resume exists and jd length is valid', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <BrowserRouter>
        <AnalyzePage />
      </BrowserRouter>
    )

    const submitBtn = screen.getByRole('button', { name: /run adaptive analysis/i })
    const jdInput = screen.getByPlaceholderText(/paste the full job description here/i)
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement | null

    expect(fileInput).not.toBeNull()
    if (!fileInput) {
      throw new Error('file input not found')
    }

    const resume = new File(['resume content'], 'resume.txt', { type: 'text/plain' })
    await user.upload(fileInput, resume)

    await user.clear(jdInput)
    await user.type(jdInput, 'short jd')
    expect(submitBtn).toBeDisabled()
    expect(screen.getByText(/add more job description text/i)).toBeInTheDocument()

    await user.clear(jdInput)
    await user.type(
      jdInput,
      'Senior backend engineer role requiring Python, APIs, SQL, Docker, and testing experience.'
    )

    expect(submitBtn).toBeEnabled()
  })

  it('shows loading pipeline and progress stage updates while analysis is running', async () => {
    const user = userEvent.setup()
    vi.mocked(runAnalysis).mockImplementation(() => new Promise(() => {}) as any)

    const { container } = render(
      <BrowserRouter>
        <AnalyzePage />
      </BrowserRouter>
    )

    const jdInput = screen.getByPlaceholderText(/paste the full job description here/i)
    const submitBtn = screen.getByRole('button', { name: /run adaptive analysis/i })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement | null

    expect(fileInput).not.toBeNull()
    if (!fileInput) {
      throw new Error('file input not found')
    }

    const resume = new File(['resume content'], 'resume.txt', { type: 'text/plain' })
    await user.upload(fileInput, resume)
    await user.type(
      jdInput,
      'Senior backend engineer role requiring Python, APIs, SQL, Docker, and testing experience.'
    )

    expect(submitBtn).toBeEnabled()

    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/running analysis pipeline/i)).toBeInTheDocument()
    })
    expect(screen.getAllByText(/parsing engine/i).length).toBeGreaterThan(0)
    expect(runAnalysis).toHaveBeenCalledTimes(1)
  })
})
