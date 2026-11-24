import { ChevronLeft, ChevronRight, MapPin, Monitor } from 'lucide-react'
import { useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import {
  cardClassName,
  EmptyState,
  FeatureError,
  PageHeader,
  TabBar,
} from '../../components/FeatureState'
import { inputClassName, labelClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { LocationSelect, UnitSelect } from '../../components/Pickers'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { formatDate, formatDateTime, todayIsoDate } from '../../lib/format'
import { EVENT_STATUSES, type CalendarFilters, type CalendarItem, type EventStatus } from '../../types/training'
import { useAuth } from '../auth/authContext'
import {
  addDays,
  addMonths,
  endOfMonth,
  fromIso,
  itemsOnDay,
  monthGridDays,
  monthOnlyItems,
  startOfMonth,
  weekDays,
} from './calendarDates'
import { EventStatusBadge } from './TrainingParts'
import { useNominationText } from './trainingLabels'
import { useCalendar, useCalendarLabels } from './trainingQueries'

type View = 'month' | 'week' | 'list'

/**
 * Training calendar derived from the register (sessions, or the event's dates when it
 * has no sessions). The server narrows it to the user's scope; "My schedule" shows only
 * the signed-in employee's own training.
 */
export function TrainingCalendarPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const { user } = useAuth()
  const [view, setView] = useState<View>('month')
  const [anchor, setAnchor] = useState(() => todayIsoDate())
  const [mine, setMine] = useState(false)
  const [unit, setUnit] = useState('')
  const [location, setLocation] = useState('')
  const [status, setStatus] = useState<EventStatus | ''>('')
  const [label, setLabel] = useState('')
  const labels = useCalendarLabels()
  const narrow = !useMediaQuery('(min-width: 768px)')
  const ids = { mine: useId(), status: useId(), label: useId() }

  const days = useMemo(() => (view === 'week' ? weekDays(anchor) : monthGridDays(anchor)), [view, anchor])
  const range =
    view === 'list'
      ? { start: startOfMonth(anchor), end: endOfMonth(anchor) }
      : { start: days[0], end: days[days.length - 1] }
  const filters: CalendarFilters = {
    start: range.start,
    end: range.end,
    mine,
    unit: unit || undefined,
    location: location || undefined,
    status: status || undefined,
    calendar_label: label || undefined,
  }
  const calendar = useCalendar(filters, user !== null)

  const step = (direction: 1 | -1) =>
    setAnchor((current) => (view === 'week' ? addDays(current, 7 * direction) : addMonths(current, direction)))
  const heading =
    view === 'week'
      ? `${formatDate(days[0], language)} – ${formatDate(days[6], language)}`
      : new Intl.DateTimeFormat(language, { month: 'long', year: 'numeric' }).format(fromIso(anchor))

  return (
    <div className="space-y-6">
      <PageHeader title={t('training.calendar.title')} description={t('training.calendar.description')} />

      <div className={`${cardClassName} grid gap-4 sm:grid-cols-2 lg:grid-cols-4`}>
        <UnitSelect label={t('training.fields.orgUnit')} value={unit} onChange={setUnit} />
        <LocationSelect label={t('training.fields.location')} value={location} onChange={setLocation} />
        <div className="space-y-1.5">
          <label htmlFor={ids.status} className={labelClassName}>
            {t('training.fields.status')}
          </label>
          <select id={ids.status} value={status} onChange={(e) => setStatus(e.target.value as EventStatus | '')} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {EVENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`training.status.${s}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.label} className={labelClassName}>
            {t('training.fields.calendarLabel')}
          </label>
          <select id={ids.label} value={label} onChange={(e) => setLabel(e.target.value)} className={inputClassName()}>
            <option value="">{t('training.register.any')}</option>
            {(labels.data ?? []).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <label htmlFor={ids.mine} className="flex items-center gap-2 text-sm font-medium text-slate-800">
          <input id={ids.mine} type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} className="size-4 accent-brand-700" />
          {t('training.calendar.mine')}
        </label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => step(-1)} aria-label={t('training.calendar.previous')} className={secondaryButtonClassName}>
            <ChevronLeft aria-hidden="true" className="size-4" />
          </button>
          <button type="button" onClick={() => setAnchor(todayIsoDate())} className={secondaryButtonClassName}>
            {t('training.calendar.today')}
          </button>
          <button type="button" onClick={() => step(1)} aria-label={t('training.calendar.next')} className={secondaryButtonClassName}>
            <ChevronRight aria-hidden="true" className="size-4" />
          </button>
          <h2 className="ml-2 text-lg font-semibold text-slate-900" aria-live="polite">
            {heading}
          </h2>
        </div>
        <TabBar<View>
          label={t('training.calendar.view')}
          value={view}
          onChange={setView}
          tabs={[
            { value: 'month', label: t('training.calendar.month') },
            { value: 'week', label: t('training.calendar.week') },
            { value: 'list', label: t('training.calendar.list') },
          ]}
        />
      </div>

      {calendar.isPending ? (
        <LoadingState />
      ) : calendar.isError ? (
        <FeatureError error={calendar.error} title={t('training.calendar.loadError')} onRetry={() => void calendar.refetch()} />
      ) : (
        <>
          <p className="text-xs text-slate-600">{t(`training.scope.${calendar.data.scope}`)}</p>
          <MonthOnly items={monthOnlyItems(calendar.data.items)} />
          {view === 'list' || narrow ? (
            <Agenda items={calendar.data.items.filter((i) => !i.month_only)} days={view === 'list' ? null : days} />
          ) : (
            <Grid days={days} items={calendar.data.items} anchor={anchor} weekView={view === 'week'} />
          )}
        </>
      )}
    </div>
  )
}

function ItemLink({ item, compact = false }: { item: CalendarItem; compact?: boolean }) {
  const { t, i18n } = useTranslation()
  const nomination = useNominationText()
  const time = item.starts_at
    ? formatDateTime(item.starts_at, i18n.resolvedLanguage, { timeStyle: 'short' })
    : t('training.calendar.allDay')
  // A cancelled session of a still-running event is shown as cancelled, not scheduled.
  const sessionCancelled = item.session?.status === 'cancelled' && item.event.status !== 'cancelled'
  const tone =
    item.event.status === 'cancelled' || sessionCancelled
      ? 'border-red-200 bg-red-50 text-red-900 line-through'
      : item.event.status === 'completed'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
        : item.event.status === 'scheduled'
          ? 'border-brand-200 bg-brand-50 text-brand-900'
          : 'border-slate-200 bg-white text-slate-800'
  return (
    <Link
      to={`/training/events/${item.event.public_id}`}
      className={`block rounded border px-1.5 py-1 text-xs hover:shadow focus:ring-2 focus:ring-brand-500 focus:outline-none ${tone}`}
    >
      <span className="font-medium">{time}</span> {item.event.title}
      {compact && sessionCancelled ? <span className="sr-only"> ({t('training.calendar.sessionCancelled')})</span> : null}
      {!compact ? (
        <span className="mt-0.5 block text-[11px] opacity-80">
          {sessionCancelled ? t('training.calendar.sessionCancelled') : t(`training.status.${item.event.status}`)}
          {item.my_status ? ` · ${t('training.calendar.myStatus', { status: nomination(item.my_status) })}` : ''}
        </span>
      ) : null}
    </Link>
  )
}

function Grid({
  days,
  items,
  anchor,
  weekView,
}: {
  days: string[]
  items: CalendarItem[]
  anchor: string
  weekView: boolean
}) {
  const { i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const today = todayIsoDate()
  const month = anchor.slice(0, 7)
  const weekdayNames = days.slice(0, 7).map((day) => new Intl.DateTimeFormat(language, { weekday: 'short' }).format(fromIso(day)))
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <div role="grid" aria-label={anchor} className="grid min-w-[700px] grid-cols-7">
        {weekdayNames.map((name) => (
          <div key={name} role="columnheader" className="border-b border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600">
            {name}
          </div>
        ))}
        {days.map((day) => {
          const dayItems = itemsOnDay(items, day)
          const outside = !weekView && day.slice(0, 7) !== month
          return (
            <div
              key={day}
              role="gridcell"
              aria-label={formatDate(day, language)}
              className={`${weekView ? 'min-h-48' : 'min-h-28'} space-y-1 border-r border-b border-slate-100 p-1.5 ${outside ? 'bg-slate-50/60' : ''}`}
            >
              <p className={`text-xs font-medium ${day === today ? 'inline-block rounded-full bg-brand-700 px-1.5 text-white' : outside ? 'text-slate-400' : 'text-slate-700'}`}>
                {fromIso(day).getDate()}
              </p>
              {dayItems.map((item) => (
                <ItemLink key={`${item.event.public_id}-${item.session?.public_id ?? 'all'}`} item={item} compact={!weekView} />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Agenda({ items, days }: { items: CalendarItem[]; days: string[] | null }) {
  const { t, i18n } = useTranslation()
  const nomination = useNominationText()
  const language = i18n.resolvedLanguage
  const groups = new Map<string, CalendarItem[]>()
  const candidates = days ?? [...new Set(items.map((i) => i.start_date).filter((d): d is string => d !== null))].sort()
  for (const day of candidates) {
    const list = days ? itemsOnDay(items, day) : items.filter((i) => i.start_date === day)
    if (list.length > 0) groups.set(day, list)
  }
  if (groups.size === 0) return <EmptyState title={t('training.calendar.empty')} />
  return (
    <ol className="space-y-4">
      {[...groups.entries()].map(([day, list]) => (
        <li key={day}>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">
            {new Intl.DateTimeFormat(language, { weekday: 'long', day: 'numeric', month: 'long' }).format(fromIso(day))}
          </h3>
          <ul className="space-y-2">
            {list.map((item) => (
              <li key={`${item.event.public_id}-${item.session?.public_id ?? 'all'}`} className={`${cardClassName} space-y-1`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link to={`/training/events/${item.event.public_id}`} className="font-medium text-brand-700 hover:underline">
                    {item.event.title}
                  </Link>
                  <EventStatusBadge status={item.event.status} />
                </div>
                <p className="text-sm text-slate-700">
                  {item.starts_at && item.ends_at
                    ? `${formatDateTime(item.starts_at, language, { timeStyle: 'short' })} – ${formatDateTime(item.ends_at, language, { timeStyle: 'short' })}`
                    : t('training.calendar.allDay')}
                </p>
                <p className="flex flex-wrap gap-3 text-xs text-slate-600">
                  {item.venue ? (
                    <span className="inline-flex items-center gap-1">
                      <MapPin aria-hidden="true" className="size-3.5" />
                      {item.venue}
                    </span>
                  ) : null}
                  {item.online ? (
                    <span className="inline-flex items-center gap-1">
                      <Monitor aria-hidden="true" className="size-3.5" />
                      {t('training.calendar.online')}
                    </span>
                  ) : null}
                  {item.org_unit ? <span>{item.org_unit.name}</span> : null}
                  {item.my_status ? <span>{t('training.calendar.myStatus', { status: nomination(item.my_status) })}</span> : null}
                </p>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ol>
  )
}

function MonthOnly({ items }: { items: CalendarItem[] }) {
  const { t } = useTranslation()
  if (items.length === 0) return null
  return (
    <section aria-labelledby="month-only" className="rounded-xl border border-dashed border-slate-300 bg-white p-3">
      <h3 id="month-only" className="mb-2 text-sm font-semibold text-slate-800">
        {t('training.calendar.monthOnly')}
      </h3>
      <ul className="flex flex-wrap gap-2">
        {items.map((item) => (
          <li key={item.event.public_id}>
            <ItemLink item={item} compact />
          </li>
        ))}
      </ul>
    </section>
  )
}
