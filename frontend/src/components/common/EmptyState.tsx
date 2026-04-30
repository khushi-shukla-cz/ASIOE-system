import { ReactNode } from 'react'
import { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    variant?: 'primary' | 'secondary'
  }
  children?: ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  children,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`empty-state min-h-80 ${className}`}
      role="status"
      aria-label={title}
    >
      <div className="empty-state-icon">
        <Icon size={28} className="text-slate-400" />
      </div>
      <h2 className="font-display text-2xl text-slate-800 mb-2">{title}</h2>
      {description && <p className="text-slate-400 text-sm mb-6 max-w-sm">{description}</p>}
      {children && <div className="mb-6">{children}</div>}
      {action && (
        <button
          onClick={action.onClick}
          className={`
            inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm
            transition-all duration-200 focus-visible:outline-offset-2
            ${
              action.variant === 'secondary'
                ? 'btn-secondary'
                : 'btn-primary'
            }
          `}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

export default EmptyState
