import { Eye } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '../../components/ErrorState'
import { ApiError } from '../../lib/apiClient'
import { describeApiError } from '../auth/authErrors'
import { TABLE_LAYOUTS, type TableLayout } from './tableLayouts'

/** Shared building blocks for the read-only administration pages. */

export function AdminPageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  const { t } = useTranslation()
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">{title}</h1>
        <p className="max-w-3xl text-slate-600">{subtitle}</p>
      </div>
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
        <Eye aria-hidden="true" className="size-3.5" />
        {t('admin.readOnly')}
      </span>
    </header>
  )
}

export function AdminErrorState({
  title,
  error,
  onRetry,
  isRetrying,
}: {
  title: string
  error: unknown
  onRetry: () => void
  isRetrying: boolean
}) {
  const { t } = useTranslation()
  if (error instanceof ApiError && error.status === 403) {
    return <ErrorState title={title} message={t('admin.noPermission')} />
  }
  const described = describeApiError(error)
  const message = described.requestId
    ? `${t(described.key)} ${t('auth.errors.reference', { requestId: described.requestId })}`
    : t(described.key)
  return <ErrorState title={title} message={message} onRetry={onRetry} isRetrying={isRetrying} />
}

/** A table cell that becomes a labelled row when the table is stacked. */
export function Cell({
  label,
  layout = 'md',
  children,
}: {
  label: string
  layout?: TableLayout
  children: ReactNode
}) {
  const classes = TABLE_LAYOUTS[layout]
  return (
    <td className={classes.cell}>
      <span className={classes.label}>{label}</span>
      <span className="min-w-0 break-words">{children}</span>
    </td>
  )
}

export function HeaderCell({ children }: { children: ReactNode }) {
  return (
    <th scope="col" className="px-4 py-3 text-xs font-semibold text-slate-600">
      {children}
    </th>
  )
}
