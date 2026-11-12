import { useTranslation } from 'react-i18next'

import type { ApiConnectionState } from '../features/system-status/useApiStatus'
import { useApiStatus } from '../features/system-status/useApiStatus'

const DOT_CLASSES: Record<ApiConnectionState, string> = {
  checking: 'bg-slate-400 animate-pulse',
  online: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  offline: 'bg-red-500',
}

export function ConnectivityIndicator() {
  const { t } = useTranslation()
  const { state } = useApiStatus()
  const label = t(`status.${state}`)

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`${t('status.indicatorLabel')}: ${label}`}
      data-state={state}
      title={label}
      className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-xs font-medium text-white"
    >
      <span aria-hidden="true" className={`size-2.5 shrink-0 rounded-full ${DOT_CLASSES[state]}`} />
      <span className="hidden max-w-48 truncate sm:inline">{label}</span>
    </div>
  )
}
