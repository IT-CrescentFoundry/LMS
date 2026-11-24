import { useTranslation } from 'react-i18next'

import {
  ATTENDANCE_STATUSES,
  COMPLETION_STATUSES,
  NOMINATION_STATUSES,
  type EventStatus,
  type Timeframe,
} from '../../types/training'

const BADGE = 'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap'

const STATUS_TONE: Record<EventStatus, string> = {
  planned: 'bg-slate-100 text-slate-800 ring-slate-300',
  scheduled: 'bg-brand-50 text-brand-800 ring-brand-200',
  completed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  postponed: 'bg-amber-50 text-amber-900 ring-amber-200',
  cancelled: 'bg-red-50 text-red-800 ring-red-200',
}

const TIMEFRAME_TONE: Record<Timeframe, string> = {
  past: 'bg-slate-50 text-slate-700 ring-slate-200',
  ongoing: 'bg-gold-50 text-slate-900 ring-gold-300',
  upcoming: 'bg-sky-50 text-sky-900 ring-sky-200',
  unscheduled: 'bg-white text-slate-600 ring-slate-300',
  cancelled: 'bg-red-50 text-red-800 ring-red-200',
}

export function EventStatusBadge({ status }: { status: EventStatus }) {
  const { t } = useTranslation()
  return <span className={`${BADGE} ${STATUS_TONE[status]}`}>{t(`training.status.${status}`)}</span>
}

export function TimeframeBadge({ timeframe }: { timeframe: Timeframe }) {
  const { t } = useTranslation()
  return <span className={`${BADGE} ${TIMEFRAME_TONE[timeframe]}`}>{t(`training.timeframe.${timeframe}`)}</span>
}

export function NominationBadge({ value }: { value: string }) {
  const { t } = useTranslation()
  const known = (NOMINATION_STATUSES as readonly string[]).includes(value)
  const tone = value === 'withdrawn' ? 'bg-slate-100 text-slate-600 ring-slate-300' : 'bg-brand-50 text-brand-800 ring-brand-200'
  return (
    <span className={`${BADGE} ${tone}`}>
      {known ? t(`training.nomination.${value as (typeof NOMINATION_STATUSES)[number]}`) : value}
    </span>
  )
}

export function AttendanceBadge({ value }: { value: string | null }) {
  const { t } = useTranslation()
  if (value === null || !(ATTENDANCE_STATUSES as readonly string[]).includes(value)) {
    return <span className={`${BADGE} bg-white text-slate-500 ring-slate-300`}>{t('training.notRecorded')}</span>
  }
  const tone =
    value === 'present' || value === 'partial'
      ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
      : 'bg-amber-50 text-amber-900 ring-amber-200'
  return (
    <span className={`${BADGE} ${tone}`}>{t(`training.attendance.${value as (typeof ATTENDANCE_STATUSES)[number]}`)}</span>
  )
}

export function CompletionBadge({ value }: { value: string | null }) {
  const { t } = useTranslation()
  if (value === null || !(COMPLETION_STATUSES as readonly string[]).includes(value)) {
    return <span className={`${BADGE} bg-white text-slate-500 ring-slate-300`}>{t('training.notRecorded')}</span>
  }
  const tone = value === 'completed' ? 'bg-emerald-50 text-emerald-800 ring-emerald-200' : 'bg-amber-50 text-amber-900 ring-amber-200'
  return (
    <span className={`${BADGE} ${tone}`}>{t(`training.completion.${value as (typeof COMPLETION_STATUSES)[number]}`)}</span>
  )
}

