import { DatabaseZap } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ApiError } from '../lib/apiClient'
import { ErrorState } from './ErrorState'
import { isSchemaPending } from '../lib/featureErrors'

/**
 * Friendly, non-alarming notice for a module whose tables are installed by a migration
 * that an administrator still has to approve and apply.
 */
export function SchemaPendingNotice({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation()
  return (
    <div
      role="status"
      className="flex gap-3 rounded-lg border border-gold-300 bg-gold-50 p-4 text-slate-800"
    >
      <DatabaseZap aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-gold-600" />
      <div className="space-y-1">
        <p className="font-medium">{t('feature.schemaPending.title')}</p>
        {compact ? null : <p className="text-sm text-slate-700">{t('feature.schemaPending.body')}</p>}
      </div>
    </div>
  )
}

/**
 * Error display for feature pages: the migration notice for 503
 * `schema_migration_pending`, otherwise the standard error with retry.
 */
export function FeatureError({
  error,
  title,
  onRetry,
}: {
  error: unknown
  title: string
  onRetry?: () => void
}) {
  if (isSchemaPending(error)) return <SchemaPendingNotice />
  const message = error instanceof ApiError && error.kind === 'http' ? error.message : undefined
  return <ErrorState title={title} message={message} onRetry={onRetry} />
}

/** Page heading with optional description and actions. */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {description ? <p className="max-w-3xl text-sm text-slate-600">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  )
}

/** Accessible tab bar (buttons with aria-pressed, wrapping on phones). */
export function TabBar<T extends string>({
  label,
  tabs,
  value,
  onChange,
}: {
  label: string
  tabs: readonly { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          aria-pressed={value === tab.value}
          onClick={() => onChange(tab.value)}
          className={`rounded-full px-3 py-1.5 text-sm font-medium focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 focus:outline-none ${
            value === tab.value
              ? 'bg-brand-700 text-white shadow-sm'
              : 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

/** Small labelled value used in detail views. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</dt>
      <dd className="mt-0.5 text-sm break-words text-slate-900">{children}</dd>
    </div>
  )
}

/** Empty-state panel. */
export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
      <p className="font-medium text-slate-800">{title}</p>
      {body ? <p className="mt-1 text-sm text-slate-600">{body}</p> : null}
    </div>
  )
}

export const cardClassName = 'rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5'
export const tableWrapClassName = 'overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm'
export const tableClassName = 'min-w-full divide-y divide-slate-200 text-sm'
export const thClassName = 'px-3 py-2 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase'
export const tdClassName = 'px-3 py-2 align-top text-slate-800'
