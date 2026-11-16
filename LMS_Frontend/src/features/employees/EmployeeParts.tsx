import { CalendarDays, ChevronRight, CircleHelp } from 'lucide-react'
import { useId, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { ErrorState } from '../../components/ErrorState'
import { inputClassName, labelClassName, secondaryButtonClassName } from '../../components/formStyles'
import { ApiError } from '../../lib/apiClient'
import { formatDate } from '../../lib/format'
import type { EmployeeRef, EmploymentStatus } from '../../types/employee'
import type { Ref } from '../../types/organisation'
import { endToLastDay } from './dates'
import { describeEmployeeError } from './employeeErrors'
import { useEmployeeErrorMessage } from './employeeErrorMessage'

const BADGE = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset'

const STATUS_TONE: Record<EmploymentStatus, string> = {
  active: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  on_leave: 'bg-amber-50 text-amber-900 ring-amber-200',
  separated: 'bg-slate-100 text-slate-700 ring-slate-300',
}

/**
 * Employment status. "Not recorded" (null) has its own dashed, neutral badge with
 * an icon and is never shown in the colours or words of "Active".
 */
export function EmploymentStatusBadge({ status }: { status: EmploymentStatus | null }) {
  const { t } = useTranslation()
  if (status === null) {
    return (
      <span
        className={`${BADGE} border border-dashed border-slate-400 bg-white text-slate-700 ring-0`}
        data-status="unknown"
      >
        <CircleHelp aria-hidden="true" className="size-3.5" />
        {t('emp.status.unknown')}
      </span>
    )
  }
  return (
    <span className={`${BADGE} ${STATUS_TONE[status]}`} data-status={status}>
      {t(`emp.status.${status}`)}
    </span>
  )
}

/** Has / has no login account that is not disabled. */
export function AccountBadge({ active }: { active: boolean }) {
  const { t } = useTranslation()
  return active ? (
    <span className={`${BADGE} bg-brand-50 text-brand-800 ring-brand-200`}>{t('emp.account.hasAccount')}</span>
  ) : (
    <span className={`${BADGE} bg-slate-50 text-slate-600 ring-slate-200`}>{t('emp.account.noAccount')}</span>
  )
}

/** "From 1 Jan 2026 · Last day 30 Jun 2026" - the end is shown as the last day in effect. */
export function RecordPeriod({ from, to }: { from: string | null; to: string | null }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const lastDay = endToLastDay(to)
  const start = from ? formatDate(from, language) : t('emp.common.startNotRecorded')
  return (
    <span className="text-slate-700">
      {t('emp.common.from', { date: start })}
      {' · '}
      {lastDay ? t('emp.common.lastDay', { date: formatDate(lastDay, language) }) : t('emp.common.ongoing')}
    </span>
  )
}

/** Organisation path as computed by the server for the requested date (root first). */
export function OrgPath({ path, unit }: { path: readonly Ref[]; unit: Ref | null }) {
  const { t } = useTranslation()
  if (unit === null) return <span className="text-slate-500">{t('emp.common.noPrimaryUnit')}</span>
  return (
    <span className="inline-flex flex-wrap items-center gap-x-1 text-slate-800">
      {path.map((item) => (
        <span key={item.public_id} className="inline-flex items-center gap-1 text-slate-600">
          <span title={item.code}>{item.name}</span>
          <ChevronRight aria-hidden="true" className="size-3.5 text-slate-400" />
        </span>
      ))}
      <span title={unit.code} className="font-medium">
        {unit.name}
      </span>
    </span>
  )
}

export function EmployeeLink({ employee }: { employee: Pick<EmployeeRef, 'public_id' | 'employee_code' | 'full_name'> }) {
  return (
    <Link
      to={`/employees/${employee.public_id}`}
      className="rounded font-medium text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
    >
      <span className="font-mono">{employee.employee_code}</span> · {employee.full_name}
    </Link>
  )
}

/** Load failure of an employee view (403 explains the missing permission). */
export function EmployeeErrorState({
  title,
  error,
  onRetry,
  isRetrying,
}: {
  title: string
  error: unknown
  onRetry?: () => void
  isRetrying?: boolean
}) {
  const { t } = useTranslation()
  const message = useEmployeeErrorMessage()
  if (error instanceof ApiError && error.status === 403) {
    return <ErrorState title={title} message={t('admin.noPermission')} />
  }
  const notFound = error instanceof ApiError && error.status === 404
  return (
    <ErrorState
      title={title}
      message={message(describeEmployeeError(error))}
      onRetry={notFound ? undefined : onRetry}
      isRetrying={isRetrying}
    />
  )
}

/** Date for which the employee's organisational context is shown ('' = today). */
export function AsOfControl({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { t } = useTranslation()
  const id = useId()
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="space-y-1.5">
        <label htmlFor={id} className={labelClassName}>
          {t('emp.common.asOf')}
        </label>
        <input
          id={id}
          type="date"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={inputClassName()}
        />
      </div>
      <button
        type="button"
        onClick={() => onChange('')}
        disabled={value === ''}
        className={secondaryButtonClassName}
      >
        <CalendarDays aria-hidden="true" className="size-4" />
        {t('emp.common.today')}
      </button>
    </div>
  )
}

/** Small "label: value" pair for detail panels (definition list item). */
export function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-0.5">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="break-words text-sm text-slate-900">{children}</dd>
    </div>
  )
}
