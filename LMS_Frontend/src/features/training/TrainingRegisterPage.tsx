import { CalendarDays, Pencil, Plus } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router'

import {
  cardClassName,
  EmptyState,
  FeatureError,
  PageHeader,
  TabBar,
  tableClassName,
  tableWrapClassName,
  tdClassName,
  thClassName,
} from '../../components/FeatureState'
import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { DesignationSelect, LocationSelect, UnitSelect } from '../../components/Pickers'
import { EVENT_PAGE_SIZE } from '../../services/trainingService'
import {
  ATTENDANCE_STATUSES,
  COMPLETION_STATUSES,
  EVENT_STATUSES,
  TIMEFRAMES,
  type EventFilters,
  type ParticipationFilters,
  type Programme,
} from '../../types/training'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { EventFormDialog, ProgrammeDialog } from './EventDialogs'
import { AttendanceBadge, CompletionBadge, EventStatusBadge, NominationBadge, TimeframeBadge } from './TrainingParts'
import { useDeliveryModeLabel, useWhenText } from './trainingLabels'
import { useCalendarLabels, useEvents, useParticipations, useProgrammes, useRegisterSummary } from './trainingQueries'

type Tab = 'events' | 'records' | 'programmes'

/**
 * Central training records register: summary of recorded facts, the events register,
 * employee participation records and the programme catalogue.
 */
export function TrainingRegisterPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = (['events', 'records', 'programmes'] as const).find((value) => value === params.get('tab')) ?? 'events'
  const canManage = useHasPermission(PERMISSIONS.TRAINING_EVENTS_MANAGE)
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('training.register.title')}
        description={t('training.register.description')}
        actions={
          <>
            <Link to="/training/calendar" className={secondaryButtonClassName}>
              <CalendarDays aria-hidden="true" className="size-4" />
              {t('nav.trainingCalendar')}
            </Link>
            {canManage ? (
              <button type="button" onClick={() => setCreating(true)} className={primaryButtonClassName}>
                <Plus aria-hidden="true" className="size-4" />
                {t('training.register.newEvent')}
              </button>
            ) : null}
          </>
        }
      />
      <SummaryCards />
      <TabBar<Tab>
        label={t('training.register.tabs.label')}
        value={tab}
        onChange={(next) => setParams(next === 'events' ? {} : { tab: next })}
        tabs={[
          { value: 'events', label: t('training.register.tabs.events') },
          { value: 'records', label: t('training.register.tabs.records') },
          { value: 'programmes', label: t('training.register.tabs.programmes') },
        ]}
      />
      {tab === 'events' ? <EventsTab /> : tab === 'records' ? <RecordsTab /> : <ProgrammesTab canManage={canManage} />}
      {creating ? (
        <EventFormDialog
          event={null}
          onClose={() => setCreating(false)}
          onSaved={(event) => navigate(`/training/events/${event.public_id}`)}
        />
      ) : null}
    </div>
  )
}

function SummaryCards() {
  const { t, i18n } = useTranslation()
  const summary = useRegisterSummary({})
  if (summary.isPending) return <LoadingState />
  if (summary.isError) return <FeatureError error={summary.error} title={t('training.register.summaryError')} onRetry={() => void summary.refetch()} />
  const s = summary.data
  const n = (value: number) => new Intl.NumberFormat(i18n.resolvedLanguage).format(value)
  const cards = [
    { label: t('training.summary.total'), value: s.events_total },
    { label: t('training.summary.upcoming'), value: s.events_upcoming },
    { label: t('training.summary.planned'), value: s.events_planned },
    { label: t('training.summary.scheduled'), value: s.events_scheduled },
    { label: t('training.summary.completed'), value: s.events_completed },
    { label: t('training.summary.participations'), value: s.participations },
    { label: t('training.summary.attended'), value: s.attendance_recorded_present },
    { label: t('training.summary.completions'), value: s.completions_recorded },
  ]
  return (
    <section aria-labelledby="register-summary" className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="register-summary" className="text-base font-semibold text-slate-900">
          {t('training.summary.title')}
        </h2>
        <p className="text-xs text-slate-600">{t(`training.scope.${s.scope}`)}</p>
      </div>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {cards.map((card) => (
          <li key={card.label} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <p className="text-xs text-slate-600">{card.label}</p>
            <p className="text-xl font-semibold text-brand-800">{n(card.value)}</p>
          </li>
        ))}
      </ul>
      <p className="text-xs text-slate-500">{t('training.summary.note')}</p>
    </section>
  )
}

// --------------------------------------------------------------------------- events

function EventsTab() {
  const { t, i18n } = useTranslation()
  const [draft, setDraft] = useState<EventFilters>({})
  const [filters, setFilters] = useState<EventFilters>({})
  const [offset, setOffset] = useState(0)
  const events = useEvents(filters, offset)
  const labels = useCalendarLabels()
  const when = useWhenText()
  const mode = useDeliveryModeLabel()
  const ids = { q: useId(), status: useId(), timeframe: useId(), label: useId(), from: useId(), to: useId() }
  const set = <K extends keyof EventFilters>(key: K, value: EventFilters[K]) => setDraft((d) => ({ ...d, [key]: value }))

  function apply(e: FormEvent) {
    e.preventDefault()
    setOffset(0)
    const clean: EventFilters = {}
    for (const [key, value] of Object.entries(draft)) if (value) (clean as Record<string, string>)[key] = value
    setFilters(clean)
  }

  return (
    <div className="space-y-4">
      <form role="search" aria-label={t('training.register.filters')} onSubmit={apply} className={`${cardClassName} grid gap-4 sm:grid-cols-2 lg:grid-cols-4`}>
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor={ids.q} className={labelClassName}>
            {t('training.register.search')}
          </label>
          <input id={ids.q} type="search" value={draft.q ?? ''} onChange={(e) => set('q', e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.status} className={labelClassName}>
            {t('training.fields.status')}
          </label>
          <select id={ids.status} value={draft.status ?? ''} onChange={(e) => set('status', e.target.value as EventFilters['status'])} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {EVENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`training.status.${s}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.timeframe} className={labelClassName}>
            {t('training.fields.timeframe')}
          </label>
          <select id={ids.timeframe} value={draft.timeframe ?? ''} onChange={(e) => set('timeframe', e.target.value as EventFilters['timeframe'])} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {TIMEFRAMES.map((s) => (
              <option key={s} value={s}>
                {t(`training.timeframe.${s}`)}
              </option>
            ))}
          </select>
        </div>
        <UnitSelect label={t('training.fields.orgUnit')} value={draft.unit ?? ''} onChange={(v) => set('unit', v)} />
        <LocationSelect label={t('training.fields.location')} value={draft.location ?? ''} onChange={(v) => set('location', v)} />
        <div className="space-y-1.5">
          <label htmlFor={ids.label} className={labelClassName}>
            {t('training.fields.calendarLabel')}
          </label>
          <select id={ids.label} value={draft.calendar_label ?? ''} onChange={(e) => set('calendar_label', e.target.value)} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {(labels.data ?? []).map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1.5">
            <label htmlFor={ids.from} className={labelClassName}>
              {t('training.register.from')}
            </label>
            <input id={ids.from} type="date" value={draft.date_from ?? ''} onChange={(e) => set('date_from', e.target.value)} className={inputClassName()} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor={ids.to} className={labelClassName}>
              {t('training.register.to')}
            </label>
            <input id={ids.to} type="date" value={draft.date_to ?? ''} onChange={(e) => set('date_to', e.target.value)} className={inputClassName()} />
          </div>
        </div>
        <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
          <button type="submit" className={primaryButtonClassName}>
            {t('training.register.apply')}
          </button>
          <button
            type="button"
            onClick={() => {
              setDraft({})
              setFilters({})
              setOffset(0)
            }}
            className={secondaryButtonClassName}
          >
            {t('training.register.clear')}
          </button>
        </div>
      </form>

      {events.isPending ? (
        <LoadingState />
      ) : events.isError ? (
        <FeatureError error={events.error} title={t('training.register.loadError')} onRetry={() => void events.refetch()} />
      ) : events.data.items.length === 0 ? (
        <EmptyState title={t('training.register.empty')} body={t('training.register.emptyBody')} />
      ) : (
        <>
          <div className={tableWrapClassName}>
            <table className={tableClassName}>
              <caption className="sr-only">{t('training.register.caption')}</caption>
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className={thClassName}>{t('training.fields.title')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.when')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.status')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.orgUnit')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.deliveryMode')}</th>
                  <th scope="col" className={`${thClassName} text-right`}>{t('training.fields.participants')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.data.items.map((event) => (
                  <tr key={event.public_id} className="hover:bg-slate-50">
                    <td className={tdClassName}>
                      <Link to={`/training/events/${event.public_id}`} className="font-medium text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none">
                        {event.title}
                      </Link>
                      <p className="text-xs text-slate-500">
                        {event.code}
                        {event.calendar_label ? ` · ${event.calendar_label}` : ''}
                      </p>
                    </td>
                    <td className={tdClassName}>
                      {when({
                        start: event.actual_start_date ?? event.planned_start_date,
                        end: event.actual_end_date ?? event.planned_end_date,
                        planned_month: event.planned_month,
                        planned_start_date: event.planned_start_date,
                        actual_start_date: event.actual_start_date,
                      })}
                      <p className="text-xs text-slate-500">
                        {event.actual_start_date ? t('training.register.actualDates') : t('training.register.plannedDates')}
                      </p>
                    </td>
                    <td className={`${tdClassName} space-x-1 space-y-1`}>
                      <EventStatusBadge status={event.status} />
                      <TimeframeBadge timeframe={event.timeframe} />
                    </td>
                    <td className={tdClassName}>{event.org_unit?.name ?? '—'}</td>
                    <td className={tdClassName}>{mode(event.delivery_mode)}</td>
                    <td className={`${tdClassName} text-right tabular-nums`}>
                      {t('training.register.counts', {
                        participants: event.counts.participants,
                        attended: event.counts.attended,
                        completed: event.counts.completed,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager
            total={events.data.total}
            offset={offset}
            limit={EVENT_PAGE_SIZE}
            onChange={setOffset}
            language={i18n.resolvedLanguage}
          />
        </>
      )}
    </div>
  )
}

export function Pager({
  total,
  offset,
  limit,
  onChange,
  language,
}: {
  total: number
  offset: number
  limit: number
  onChange: (offset: number) => void
  language: string | undefined
}) {
  const { t } = useTranslation()
  const n = (v: number) => new Intl.NumberFormat(language).format(v)
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p role="status" aria-live="polite" className="text-sm text-slate-600">
        {t('training.register.showing', { from: n(total === 0 ? 0 : offset + 1), to: n(Math.min(offset + limit, total)), total: n(total) })}
      </p>
      <div className="flex gap-2">
        <button type="button" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))} className={secondaryButtonClassName}>
          {t('common.previous')}
        </button>
        <button type="button" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)} className={secondaryButtonClassName}>
          {t('common.next')}
        </button>
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------- records

function RecordsTab() {
  const { t, i18n } = useTranslation()
  const [draft, setDraft] = useState<ParticipationFilters>({})
  const [filters, setFilters] = useState<ParticipationFilters>({})
  const [offset, setOffset] = useState(0)
  const rows = useParticipations(filters, offset)
  const when = useWhenText()
  const ids = { q: useId(), attendance: useId(), completion: useId() }
  const set = <K extends keyof ParticipationFilters>(key: K, value: ParticipationFilters[K]) =>
    setDraft((d) => ({ ...d, [key]: value }))
  return (
    <div className="space-y-4">
      <form
        role="search"
        aria-label={t('training.records.filters')}
        onSubmit={(e) => {
          e.preventDefault()
          setOffset(0)
          const clean: ParticipationFilters = {}
          for (const [key, value] of Object.entries(draft)) if (value) (clean as Record<string, string>)[key] = value as string
          setFilters(clean)
        }}
        className={`${cardClassName} grid gap-4 sm:grid-cols-2 lg:grid-cols-4`}
      >
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor={ids.q} className={labelClassName}>
            {t('training.records.search')}
          </label>
          <input id={ids.q} type="search" value={draft.q ?? ''} onChange={(e) => set('q', e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <UnitSelect label={t('training.fields.orgUnit')} value={draft.unit ?? ''} onChange={(v) => set('unit', v)} />
        <DesignationSelect label={t('training.fields.designation')} value={draft.designation ?? ''} onChange={(v) => set('designation', v)} />
        <div className="space-y-1.5">
          <label htmlFor={ids.attendance} className={labelClassName}>
            {t('training.fields.attendance')}
          </label>
          <select id={ids.attendance} value={draft.attendance ?? ''} onChange={(e) => set('attendance', e.target.value as ParticipationFilters['attendance'])} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {ATTENDANCE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`training.attendance.${s}`)}
              </option>
            ))}
            <option value="not_recorded">{t('training.notRecorded')}</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.completion} className={labelClassName}>
            {t('training.fields.completion')}
          </label>
          <select id={ids.completion} value={draft.completion ?? ''} onChange={(e) => set('completion', e.target.value as ParticipationFilters['completion'])} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {COMPLETION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`training.completion.${s}`)}
              </option>
            ))}
            <option value="not_recorded">{t('training.notRecorded')}</option>
          </select>
        </div>
        <div className="flex items-end">
          <button type="submit" className={primaryButtonClassName}>
            {t('training.register.apply')}
          </button>
        </div>
      </form>
      {rows.isPending ? (
        <LoadingState />
      ) : rows.isError ? (
        <FeatureError error={rows.error} title={t('training.records.loadError')} onRetry={() => void rows.refetch()} />
      ) : rows.data.items.length === 0 ? (
        <EmptyState title={t('training.records.empty')} />
      ) : (
        <>
          <div className={tableWrapClassName}>
            <table className={tableClassName}>
              <caption className="sr-only">{t('training.records.caption')}</caption>
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className={thClassName}>{t('training.fields.employee')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.title')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.when')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.nomination')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.attendance')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.completion')}</th>
                  <th scope="col" className={thClassName}>{t('training.fields.certificate')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.data.items.map((row) => (
                  <tr key={row.public_id}>
                    <td className={tdClassName}>
                      {row.employee.name}
                      <p className="text-xs text-slate-500">{row.employee.employee_code}</p>
                    </td>
                    <td className={tdClassName}>
                      <Link to={`/training/events/${row.event.public_id}`} className="text-brand-700 hover:underline">
                        {row.event.title}
                      </Link>
                    </td>
                    <td className={tdClassName}>{when({ start: row.event.start, end: row.event.end })}</td>
                    <td className={tdClassName}><NominationBadge value={row.nomination_status} /></td>
                    <td className={tdClassName}><AttendanceBadge value={row.attendance_status} /></td>
                    <td className={tdClassName}><CompletionBadge value={row.completion_status} /></td>
                    <td className={tdClassName}>{row.certificate_number ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager total={rows.data.total} offset={offset} limit={50} onChange={setOffset} language={i18n.resolvedLanguage} />
        </>
      )}
    </div>
  )
}

// ----------------------------------------------------------------------- programmes

function ProgrammesTab({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const programmes = useProgrammes({ q: q.trim() || undefined, include_inactive: includeInactive })
  const [dialog, setDialog] = useState<Programme | 'new' | null>(null)
  const mode = useDeliveryModeLabel()
  const ids = { q: useId(), inactive: useId() }
  return (
    <div className="space-y-4">
      <div className={`${cardClassName} flex flex-wrap items-end gap-4`}>
        <div className="min-w-0 flex-1 space-y-1.5">
          <label htmlFor={ids.q} className={labelClassName}>
            {t('training.programmes.search')}
          </label>
          <input id={ids.q} type="search" value={q} onChange={(e) => setQ(e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <label htmlFor={ids.inactive} className="flex items-center gap-2 pb-2.5 text-sm">
          <input id={ids.inactive} type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="size-4 accent-brand-700" />
          {t('training.programmes.showInactive')}
        </label>
        {canManage ? (
          <button type="button" onClick={() => setDialog('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('training.programmes.create')}
          </button>
        ) : null}
      </div>
      {programmes.isPending ? (
        <LoadingState />
      ) : programmes.isError ? (
        <FeatureError error={programmes.error} title={t('training.programmes.loadError')} onRetry={() => void programmes.refetch()} />
      ) : programmes.data.length === 0 ? (
        <EmptyState title={t('training.programmes.empty')} />
      ) : (
        <div className={tableWrapClassName}>
          <table className={tableClassName}>
            <caption className="sr-only">{t('training.programmes.caption')}</caption>
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className={thClassName}>{t('training.fields.code')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.title')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.category')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.deliveryMode')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.status')}</th>
                {canManage ? <th scope="col" className={thClassName}><span className="sr-only">{t('training.programmes.actions')}</span></th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {programmes.data.map((p) => (
                <tr key={p.public_id}>
                  <td className={`${tdClassName} font-mono text-xs`}>{p.code}</td>
                  <td className={tdClassName}>{p.title}</td>
                  <td className={tdClassName}>{p.category ?? '—'}</td>
                  <td className={tdClassName}>{mode(p.default_delivery_mode)}</td>
                  <td className={tdClassName}>{p.is_active ? t('training.programmes.activeLabel') : t('training.programmes.inactiveLabel')}</td>
                  {canManage ? (
                    <td className={tdClassName}>
                      <button type="button" onClick={() => setDialog(p)} className="inline-flex items-center gap-1 text-sm text-brand-700 hover:underline">
                        <Pencil aria-hidden="true" className="size-3.5" />
                        {t('training.programmes.editShort', { title: p.title })}
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {dialog ? <ProgrammeDialog programme={dialog === 'new' ? null : dialog} onClose={() => setDialog(null)} /> : null}
    </div>
  )
}
