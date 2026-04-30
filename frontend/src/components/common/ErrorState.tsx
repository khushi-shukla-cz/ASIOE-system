import { ReactNode } from 'react'
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react'

export type ErrorStateType = 'error' | 'warning' | 'info' | 'success'

interface ErrorStateProps {
  type?: ErrorStateType
  title: string
  message?: string
  children?: ReactNode
  action?: {
    label: string
    onClick: () => void
  }
  onDismiss?: () => void
}

const styleMap = {
  error: {
    bg: 'bg-rose-50',
    border: 'border-l-4 border-rose-400',
    icon: AlertCircle,
    iconColor: 'text-rose-600',
    title: 'text-rose-900',
    message: 'text-rose-800',
  },
  warning: {
    bg: 'bg-amber-50',
    border: 'border-l-4 border-amber-400',
    icon: AlertCircle,
    iconColor: 'text-amber-600',
    title: 'text-amber-900',
    message: 'text-amber-800',
  },
  info: {
    bg: 'bg-sky-50',
    border: 'border-l-4 border-sky-400',
    icon: Info,
    iconColor: 'text-sky-600',
    title: 'text-sky-900',
    message: 'text-sky-800',
  },
  success: {
    bg: 'bg-sage-50',
    border: 'border-l-4 border-sage-400',
    icon: CheckCircle,
    iconColor: 'text-sage-600',
    title: 'text-sage-900',
    message: 'text-sage-800',
  },
}

export function ErrorState({
  type = 'error',
  title,
  message,
  children,
  action,
  onDismiss,
}: ErrorStateProps) {
  const styles = styleMap[type]
  const Icon = styles.icon

  return (
    <div
      className={`${styles.bg} ${styles.border} p-6 rounded-lg space-y-3`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <Icon size={20} className={`${styles.iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <h3 className={`font-semibold ${styles.title}`}>{title}</h3>
          {message && <p className={`text-sm ${styles.message} mt-1`}>{message}</p>}
          {children && <div className={`text-sm ${styles.message} mt-2`}>{children}</div>}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-slate-400 hover:text-slate-600 flex-shrink-0"
            aria-label="Dismiss"
          >
            <X size={18} />
          </button>
        )}
      </div>
      {action && (
        <div className="pt-2">
          <button
            onClick={action.onClick}
            className={`
              text-sm font-medium px-3 py-1.5 rounded transition-colors
              ${type === 'error' && 'bg-rose-200 text-rose-900 hover:bg-rose-300'}
              ${type === 'warning' && 'bg-amber-200 text-amber-900 hover:bg-amber-300'}
              ${type === 'info' && 'bg-sky-200 text-sky-900 hover:bg-sky-300'}
              ${type === 'success' && 'bg-sage-200 text-sage-900 hover:bg-sage-300'}
            `}
          >
            {action.label}
          </button>
        </div>
      )}
    </div>
  )
}

export default ErrorState
