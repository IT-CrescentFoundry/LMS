import { Check } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '../../components/ErrorState'
import { ApiError } from '../../lib/apiClient'
import { isRowOutcome, type ImportStatus, type IssueSeverity, type MappingStatus } from '../../types/imports'
import { currentStepIndex, IMPORT_STEPS, useImportErrorMessage, type ImportStep } from './importLabels'
import { needsReload } from './importErrors'

const BADGE = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 whitespace-nowrap'

const STATUS_TONE: Record<ImportStatus, string> = {
  uploaded: 'bg-slate-100 text-slate-700 ring-slate-300',
  mapping_required: 'bg-amber-50 text-amber-900 ring-amber-200',
  validating: 'bg-brand-50 text-brand-800 ring-brand-200',
  validation_failed: 'bg-red-50 text-red-800 ring-red-200',
  ready_for_approval: 'bg-brand-50 text-brand-800 ring-brand-200',
  committing: 'bg-brand-50 text-brand-800 ring-brand-200',
  completed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  completed_with_skips: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  failed: 'bg-red-50 text-red-800 ring-red-200',
  expired: 'bg-slate-100 text-slate-700 ring-slate-300',
  cancelled: 'bg-slate-100 text-slate-700 ring-slate-300',
}

export function ImportStatusBadge({ status }: { status: ImportStatus }) {
  const { t } = useTranslation()
  return (
    <span className={`${BADGE} ${STATUS_TONE[status]}`} data-status={status}>
      {t(`imp.status.${status}`)}
    </span>
  )
}

const OUTCOME_TONE: Record<string, string> = {
  new: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  update: 'bg-brand-50 text-brand-800 ring-brand-200',
  unchanged: 'bg-slate-100 text-slate-700 ring-slate-300',
  error: 'bg-red-50 text-red-800 ring-red-200',
  skipped: 'bg-amber-50 text-amber-900 ring-amber-200',
}

export function RowOutcomeBadge({ outcome }: { outcome: string }) {
  const { t } = useTranslation()
  return (
    <span className={`${BADGE} ${OUTCOME_TONE[outcome] ?? OUTCOME_TONE.unchanged}`}>
      {isRowOutcome(outcome) ? t(`imp.outcomes.${outcome}`) : outcome}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: IssueSeverity }) {
  const { t } = useTranslation()
  const tone =
    severity === 'error' ? 'bg-red-50 text-red-800 ring-red-200' : 'bg-amber-50 text-amber-900 ring-amber-200'
  return <span className={`${BADGE} ${tone}`}>{t(`imp.severity.${severity}`)}</span>
}

const MAPPING_TONE: Record<MappingStatus, string> = {
  pending: 'bg-amber-50 text-amber-900 ring-amber-200',
  approved: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  rejected: 'bg-red-50 text-red-800 ring-red-200',
  superseded: 'bg-slate-100 text-slate-700 ring-slate-300',
}

export function MappingStatusBadge({ status }: { status: MappingStatus }) {
  const { t } = useTranslation()
  return <span className={`${BADGE} ${MAPPING_TONE[status]}`}>{t(`imp.mappingStatus.${status}`)}</span>
}

export function ImportErrorState({
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
  const message = useImportErrorMessage()
  if (error instanceof ApiError && error.status === 403) {
    return <ErrorState title={title} message={t('admin.noPermission')} />
  }
  const notFound = error instanceof ApiError && error.status === 404
  return (
    <ErrorState
      title={title}
      message={message(error)}
      onRetry={notFound ? undefined : onRetry}
      isRetrying={isRetrying}
    />
  )
}

/** Inline error of an action, with a reload button when someone else acted first. */
export function ActionError({ error, onReload }: { error: unknown; onReload?: () => void }) {
  const { t } = useTranslation()
  const message = useImportErrorMessage()
  return (
    <div role="alert" className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <p>{message(error)}</p>
      {onReload && needsReload(error) ? (
        <button
          type="button"
          onClick={onReload}
          className="font-medium text-red-900 underline hover:no-underline focus:ring-2 focus:ring-red-400 focus:outline-none"
        >
          {t('imp.actions.reload')}
        </button>
      ) : null}
    </div>
  )
}

export function CountTile({
  label,
  value,
  tone = 'slate',
  children,
}: {
  label: string
  value: number | string
  tone?: 'slate' | 'red' | 'amber' | 'emerald' | 'brand'
  children?: ReactNode
}) {
  const tones = {
    slate: 'text-slate-900',
    red: 'text-red-700',
    amber: 'text-amber-800',
    emerald: 'text-emerald-700',
    brand: 'text-brand-700',
  }
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <dt className="text-sm break-words text-slate-600">{label}</dt>
      <dd className={`mt-1 text-2xl font-bold ${tones[tone]}`}>{value}</dd>
      {children}
    </div>
  )
}

/** Where the job is in the workflow (an ordered list; the current step is marked). */
export function StepIndicator({ step }: { step: ImportStep }) {
  const { t } = useTranslation()
  const index = currentStepIndex(step)
  return (
    <ol aria-label={t('imp.steps.label')} className="flex flex-wrap gap-2">
      {IMPORT_STEPS.map((name, position) => {
        const done = position < index
        const current = position === index
        return (
          <li
            key={name}
            aria-current={current ? 'step' : undefined}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ring-1 ${
              current
                ? 'bg-brand-700 text-white ring-brand-700'
                : done
                  ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
                  : 'bg-white text-slate-600 ring-slate-300'
            }`}
          >
            {done ? <Check aria-hidden="true" className="size-4" /> : <span aria-hidden="true">{position + 1}.</span>}
            {t(`imp.steps.${name}`)}
          </li>
        )
      })}
    </ol>
  )
}

