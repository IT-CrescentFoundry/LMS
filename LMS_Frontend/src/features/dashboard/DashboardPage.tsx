import { Bell, CalendarDays, GraduationCap, Grid3x3, Library, Network, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { cardClassName, SchemaPendingNotice } from '../../components/FeatureState'
import { isSchemaPending } from '../../lib/featureErrors'
import { formatDateTime, todayIsoDate } from '../../lib/format'
import { useAuth } from '../auth/authContext'
import {
  COMPETENCY_VIEW_PERMISSIONS,
  hasAnyPermission,
  hasPermission,
  PERMISSIONS,
  TRAINING_VIEW_PERMISSIONS,
} from '../auth/permissions'
import { useMySkills } from '../skills/competencyQueries'
import { SystemStatusPanel } from '../system-status/SystemStatusPanel'
import { addDays } from '../training/calendarDates'
import { EventStatusBadge } from '../training/TrainingParts'
import { useWhenText } from '../training/trainingLabels'
import { useCalendar, useNotifications, useRegisterSummary } from '../training/trainingQueries'

function Widget({ title, icon: Icon, children, to, linkLabel }: { title: string; icon: LucideIcon; children: ReactNode; to?: string; linkLabel?: string }) {
  return (
    <section className={`${cardClassName} space-y-3`} aria-label={title}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold text-slate-900">
          <span className="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Icon aria-hidden="true" className="size-4" />
          </span>
          {title}
        </h2>
        {to && linkLabel ? (
          <Link to={to} className="text-sm font-medium text-brand-700 hover:underline">
            {linkLabel}
          </Link>
        ) : null}
      </div>
      {children}
    </section>
  )
}

/** The signed-in employee's training in the next 30 days. */
function UpcomingWidget() {
  const { t, i18n } = useTranslation()
  const start = todayIsoDate()
  const calendar = useCalendar({ start, end: addDays(start, 30), mine: true })
  const when = useWhenText()
  if (!calendar.data) return null
  const items = calendar.data.items.filter((item) => item.event.status !== 'cancelled').slice(0, 5)
  return (
    <Widget title={t('dash.upcoming.title')} icon={CalendarDays} to="/training/calendar" linkLabel={t('dash.openCalendar')}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600">{t('dash.upcoming.empty')}</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={`${item.event.public_id}-${item.session?.public_id ?? 'all'}`} className="flex items-start justify-between gap-2 py-2 text-sm">
              <span className="min-w-0">
                <Link to={`/training/events/${item.event.public_id}`} className="font-medium text-brand-700 hover:underline">
                  {item.event.title}
                </Link>
                <span className="block text-xs text-slate-600">
                  {item.starts_at ? formatDateTime(item.starts_at, i18n.resolvedLanguage) : when({ start: item.start_date, end: item.end_date })}
                  {item.venue ? ` · ${item.venue}` : ''}
                </span>
              </span>
              <EventStatusBadge status={item.event.status} />
            </li>
          ))}
        </ul>
      )}
    </Widget>
  )
}

function RegisterWidget() {
  const { t, i18n } = useTranslation()
  const summary = useRegisterSummary({})
  if (!summary.data) return null
  const s = summary.data
  const n = (value: number) => new Intl.NumberFormat(i18n.resolvedLanguage).format(value)
  return (
    <Widget title={t('dash.register.title')} icon={GraduationCap} to="/training" linkLabel={t('dash.openRegister')}>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        {(
          [
            ['upcoming', s.events_upcoming],
            ['scheduled', s.events_scheduled],
            ['completed', s.events_completed],
            ['completions', s.completions_recorded],
          ] as const
        ).map(([key, value]) => (
          <div key={key}>
            <dt className="text-xs text-slate-600">{t(`training.summary.${key}`)}</dt>
            <dd className="text-lg font-semibold text-brand-800">{n(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-slate-500">{t(`training.scope.${s.scope}`)}</p>
    </Widget>
  )
}

function NotificationsWidget() {
  const { t } = useTranslation()
  const list = useNotifications(false)
  if (!list.data) return null
  const latest = list.data.items.slice(0, 3)
  return (
    <Widget title={t('dash.notifications.title')} icon={Bell} to="/notifications" linkLabel={t('dash.openNotifications')}>
      <p className="text-sm text-slate-700">{t('dash.notifications.unread', { count: list.data.unread_count })}</p>
      {latest.length > 0 ? (
        <ul className="space-y-1 text-sm">
          {latest.map((item) => (
            <li key={item.public_id} className={item.read_at ? 'text-slate-600' : 'font-medium text-slate-900'}>
              {item.title}
            </li>
          ))}
        </ul>
      ) : null}
    </Widget>
  )
}

function SkillsWidget() {
  const { t } = useTranslation()
  const skills = useMySkills()
  if (!skills.data || skills.data.matrices.length === 0) return null
  const totals = skills.data.matrices.reduce(
    (acc, grid) => ({
      below: acc.below + (grid.summary.below ?? 0),
      met: acc.met + (grid.summary.met ?? 0) + (grid.summary.exceeds ?? 0),
      notAssessed: acc.notAssessed + (grid.summary.not_assessed ?? 0),
    }),
    { below: 0, met: 0, notAssessed: 0 },
  )
  return (
    <Widget title={t('dash.skills.title')} icon={Grid3x3} to="/skills/me" linkLabel={t('dash.openSkills')}>
      <ul className="space-y-1 text-sm text-slate-700">
        <li>{t('dash.skills.below', { count: totals.below })}</li>
        <li>{t('dash.skills.met', { count: totals.met })}</li>
        <li>{t('dash.skills.notAssessed', { count: totals.notAssessed })}</li>
      </ul>
    </Widget>
  )
}

function QuickLinks() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const links: { to: string; label: string; icon: LucideIcon; show: boolean }[] = [
    { to: '/training', label: t('nav.trainingRecords'), icon: GraduationCap, show: hasAnyPermission(user, TRAINING_VIEW_PERMISSIONS) },
    { to: '/training/calendar', label: t('nav.trainingCalendar'), icon: CalendarDays, show: hasAnyPermission(user, TRAINING_VIEW_PERMISSIONS) },
    { to: '/skills', label: t('nav.skillMatrix'), icon: Grid3x3, show: hasAnyPermission(user, COMPETENCY_VIEW_PERMISSIONS) },
    { to: '/competencies', label: t('nav.competencyLibrary'), icon: Library, show: hasAnyPermission(user, COMPETENCY_VIEW_PERMISSIONS) },
    { to: '/organisation', label: t('nav.organisation'), icon: Network, show: hasPermission(user, PERMISSIONS.ORGANISATION_VIEW) },
  ]
  const visible = links.filter((link) => link.show)
  if (visible.length === 0) return null
  return (
    <nav aria-label={t('dash.quickLinks')} className="flex flex-wrap gap-2">
      {visible.map(({ to, label, icon: Icon }) => (
        <Link key={to} to={to} className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50">
          <Icon aria-hidden="true" className="size-4 text-brand-600" />
          {label}
        </Link>
      ))}
    </nav>
  )
}

/**
 * Permission-aware dashboard: only recorded facts, and only widgets the user may see.
 * Widgets hide themselves when their API refuses (403/404) or is unavailable; while the
 * first-release migration is pending a single notice explains why.
 */
export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const notifications = useNotifications(false)
  const pending = notifications.isError && isSchemaPending(notifications.error)
  const own = hasPermission(user, PERMISSIONS.LEARNING_OWN_VIEW)
  const register = hasAnyPermission(user, [PERMISSIONS.TRAINING_RECORDS_VIEW, PERMISSIONS.TRAINING_EVENTS_MANAGE, PERMISSIONS.TEAM_LEARNING_VIEW])

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t('dashboard.title')}</h1>
        <p className="max-w-3xl text-slate-600">{t('dash.subtitle')}</p>
      </header>
      <QuickLinks />
      {pending ? <SchemaPendingNotice /> : null}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="grid gap-6 md:grid-cols-2 lg:col-span-2">
          {!pending && own ? <UpcomingWidget /> : null}
          {!pending && register ? <RegisterWidget /> : null}
          {!pending ? <NotificationsWidget /> : null}
          {!pending && own ? <SkillsWidget /> : null}
        </div>
        <SystemStatusPanel />
      </div>
    </div>
  )
}
