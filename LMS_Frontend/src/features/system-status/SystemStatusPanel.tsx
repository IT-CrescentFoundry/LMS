import { Activity, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '../../components/ErrorState'
import { LoadingState } from '../../components/LoadingState'
import type { CheckStatus } from '../../types/health'
import { useApiStatus } from './useApiStatus'

const STATE_BADGE: Record<CheckStatus, string> = {
  ok: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  not_configured: 'bg-amber-50 text-amber-800 ring-amber-200',
  unavailable: 'bg-red-50 text-red-700 ring-red-200',
}

export function SystemStatusPanel() {
  const { t, i18n } = useTranslation()
  const { state, liveness, readiness, isFetching, lastCheckedAt, refetch } = useApiStatus()
  const databaseStatus = readiness?.checks.database?.status

  const lastChecked =
    lastCheckedAt === undefined
      ? undefined
      : new Intl.DateTimeFormat(i18n.resolvedLanguage, { timeStyle: 'medium' }).format(
          lastCheckedAt,
        )

  return (
    <section
      aria-labelledby="system-status-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-center justify-between gap-3">
        <h2
          id="system-status-heading"
          className="flex items-center gap-2 text-base font-semibold text-slate-900"
        >
          <Activity aria-hidden="true" className="size-5 text-brand-600" />
          {t('dashboard.systemStatus.title')}
        </h2>
        {state !== 'offline' && state !== 'checking' ? (
          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-50 focus:ring-2 focus:ring-brand-500 focus:outline-none disabled:opacity-60"
          >
            <RefreshCw aria-hidden="true" className={`size-4 ${isFetching ? 'animate-spin' : ''}`} />
            {t('dashboard.systemStatus.retry')}
          </button>
        ) : null}
      </div>

      <div className="mt-4">
        {state === 'checking' ? <LoadingState /> : null}

        {state === 'offline' ? (
          <ErrorState
            title={t('dashboard.systemStatus.offlineTitle')}
            message={t('dashboard.systemStatus.offlineBody')}
            onRetry={() => void refetch()}
            isRetrying={isFetching}
          />
        ) : null}

        {liveness && state !== 'offline' ? (
          <dl className="divide-y divide-slate-100 text-sm">
            <StatusRow label={t('dashboard.systemStatus.api')}>
              <StatusBadge status="ok" label={t('dashboard.systemStatus.states.ok')} />
            </StatusRow>
            <StatusRow label={t('dashboard.systemStatus.database')}>
              {databaseStatus ? (
                <StatusBadge
                  status={databaseStatus}
                  label={t(`dashboard.systemStatus.states.${databaseStatus}`)}
                />
              ) : (
                <span className="text-slate-500">…</span>
              )}
            </StatusRow>
            <StatusRow label={t('dashboard.systemStatus.version')}>
              <span className="font-mono text-slate-700">{liveness.version}</span>
            </StatusRow>
            {lastChecked ? (
              <StatusRow label={t('dashboard.systemStatus.lastChecked')}>
                <span className="text-slate-700">{lastChecked}</span>
              </StatusRow>
            ) : null}
          </dl>
        ) : null}
      </div>
    </section>
  )
}

function StatusRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-slate-600">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function StatusBadge({ status, label }: { status: CheckStatus; label: string }) {
  return (
    <span
      data-status={status}
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${STATE_BADGE[status]}`}
    >
      {label}
    </span>
  )
}
