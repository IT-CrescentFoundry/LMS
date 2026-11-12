import { CircleAlert, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface ErrorStateProps {
  title: string
  message?: string
  onRetry?: () => void
  retryLabel?: string
  isRetrying?: boolean
}

export function ErrorState({ title, message, onRetry, retryLabel, isRetrying }: ErrorStateProps) {
  const { t } = useTranslation()

  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <div className="flex gap-3">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-red-600" />
        <div className="min-w-0 space-y-1">
          <p className="font-medium">{title}</p>
          {message ? <p className="text-sm text-red-800">{message}</p> : null}
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              disabled={isRetrying}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-red-900 shadow-sm ring-1 ring-red-200 hover:bg-red-100 focus:ring-2 focus:ring-red-500 focus:outline-none disabled:opacity-60"
            >
              <RefreshCw aria-hidden="true" className={`size-4 ${isRetrying ? 'animate-spin' : ''}`} />
              {retryLabel ?? t('common.retry')}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
