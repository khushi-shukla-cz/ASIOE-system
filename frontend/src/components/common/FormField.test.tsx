import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import FormField, { Input, TextArea, Select } from './FormField'

describe('FormField', () => {
  it('renders label', () => {
    render(
      <FormField label="Test Label">
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('Test Label')).toBeInTheDocument()
  })

  it('renders required indicator when required is true', () => {
    render(
      <FormField label="Required Field" required>
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('renders error message with alert role', () => {
    render(
      <FormField label="Test" error="This field is required">
        <input type="text" />
      </FormField>
    )
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('This field is required')
  })

  it('renders hint text when provided and no error', () => {
    render(
      <FormField label="Test" hint="This is a helpful hint">
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('This is a helpful hint')).toBeInTheDocument()
  })

  it('hides hint when error is present', () => {
    render(
      <FormField
        label="Test"
        error="Error message"
        hint="This is a hint"
      >
        <input type="text" />
      </FormField>
    )
    expect(screen.queryByText('This is a hint')).not.toBeInTheDocument()
    expect(screen.getByText('Error message')).toBeInTheDocument()
  })

  it('renders children (input field)', () => {
    render(
      <FormField label="Email">
        <input type="email" placeholder="Enter email" />
      </FormField>
    )
    expect(screen.getByPlaceholderText('Enter email')).toBeInTheDocument()
  })
})

describe('Input', () => {
  it('renders input field with input-field class', () => {
    const { container } = render(
      <Input placeholder="Test" />
    )
    const input = container.querySelector('input')
    expect(input).toHaveClass('input-field')
  })

  it('sets aria-invalid when error prop is true', () => {
    const { container } = render(
      <Input error id="test-input" />
    )
    const input = container.querySelector('input')
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })

  it('sets aria-describedby when error and id provided', () => {
    const { container } = render(
      <Input error id="test-input" />
    )
    const input = container.querySelector('input')
    expect(input).toHaveAttribute('aria-describedby', 'test-input-error')
  })

  it('adds error styling when error is true', () => {
    const { container } = render(
      <Input error />
    )
    const input = container.querySelector('input')
    expect(input).toHaveClass('border-rose-400')
  })
})

describe('TextArea', () => {
  it('renders textarea with textarea-field class', () => {
    const { container } = render(
      <TextArea placeholder="Test" />
    )
    const textarea = container.querySelector('textarea')
    expect(textarea).toHaveClass('textarea-field')
  })

  it('sets aria-invalid when error prop is true', () => {
    const { container } = render(
      <TextArea error id="test-textarea" />
    )
    const textarea = container.querySelector('textarea')
    expect(textarea).toHaveAttribute('aria-invalid', 'true')
  })
})

describe('Select', () => {
  const options = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
  ]

  it('renders select with options', () => {
    render(
      <Select options={options} />
    )
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.getByText('Option 2')).toBeInTheDocument()
  })

  it('renders placeholder option when provided', () => {
    render(
      <Select options={options} placeholder="Choose an option" />
    )
    expect(screen.getByText('Choose an option')).toBeInTheDocument()
  })

  it('adds input-field class', () => {
    const { container } = render(
      <Select options={options} />
    )
    const select = container.querySelector('select')
    expect(select).toHaveClass('input-field')
  })

  it('sets aria-invalid when error is true', () => {
    const { container } = render(
      <Select options={options} error />
    )
    const select = container.querySelector('select')
    expect(select).toHaveAttribute('aria-invalid', 'true')
  })
})
