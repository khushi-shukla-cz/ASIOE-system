import { ReactNode, InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { AlertCircle } from 'lucide-react'

interface FormFieldProps {
  label: string
  error?: string
  required?: boolean
  hint?: string
  children: ReactNode
  className?: string
}

export function FormField({
  label,
  error,
  required,
  hint,
  children,
  className = '',
}: FormFieldProps) {
  const fieldId = `field-${Math.random().toString(36).substr(2, 9)}`

  return (
    <div className={`space-y-1.5 ${className}`}>
      <label htmlFor={fieldId} className="text-xs font-medium text-slate-500 mb-1.5 block uppercase tracking-wide">
        {label}
        {required && <span className="text-rose-500 ml-1">*</span>}
      </label>
      {children}
      {error && (
        <div className="flex items-center gap-1.5 text-xs text-rose-600 mt-1" role="alert">
          <AlertCircle size={13} className="flex-shrink-0" />
          {error}
        </div>
      )}
      {hint && !error && (
        <p className="text-xs text-slate-400 mt-1">{hint}</p>
      )}
    </div>
  )
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

export function Input({ error, className = '', ...props }: InputProps) {
  return (
    <input
      {...props}
      className={`input-field ${error ? 'border-rose-400 focus:ring-rose-200' : ''} ${className}`}
      aria-invalid={error}
      aria-describedby={error ? `${props.id}-error` : undefined}
    />
  )
}

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean
}

export function TextArea({ error, className = '', ...props }: TextAreaProps) {
  return (
    <textarea
      {...props}
      className={`textarea-field ${error ? 'border-rose-400 focus:ring-rose-200' : ''} ${className}`}
      aria-invalid={error}
      aria-describedby={error ? `${props.id}-error` : undefined}
    />
  )
}

interface SelectProps extends InputHTMLAttributes<HTMLSelectElement> {
  options: Array<{ value: string | number; label: string }>
  error?: boolean
  placeholder?: string
}

export function Select({
  options,
  error,
  placeholder,
  className = '',
  ...props
}: SelectProps) {
  return (
    <select
      {...(props as any)}
      className={`input-field ${error ? 'border-rose-400 focus:ring-rose-200' : ''} ${className}`}
      aria-invalid={error}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}

export default FormField
