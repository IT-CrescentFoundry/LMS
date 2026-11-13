import { useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Info, LoaderCircle, RefreshCw, RotateCcw, Search } from 'lucide-react'
import { Fragment, useId, useState, type FormEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { OutcomeBadge } from '../../components/Badges'
import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDateTime, localDayStartIso } from '../../lib/format'
import {
  AUDIT_EVENT_TYPES,
  AUDIT_OUTCOMES,
  auditEventLabel,
  isAuditTargetType,
  type AuditEvent,
  type AuditFilters,
  type AuditOutcome,
} from '../../types/admin'
import {
  AdminErrorState,
  AdminPageHeader,
  Cell,
  HeaderCell,
} from './AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from './tableLayouts'
import { adminQueryKeys, useAuditEvents, useRefreshSessionOnForbidden } from './adminQueries'

interface Draft {
  eventType: string
  outcome: AuditOutcome | ''
  from: string
  to: string
}

const EMPTY_DRAFT: Draft = { eventType: '', outcome: '', from: '', to: '' }

function toFilters(draft: Draft): AuditFilters {
  const filters: AuditFilters = {}
  if (draft.eventType) filters.event_type = draft.eventType
  if (draft.outcome) filters.outcome = draft.outcome
  const from = localDayStartIso(draft.from)
  if (from) filters.occurred_from = from
  const to = localDayStartIso(draft.to, 1) // the whole "to" day is included
  if (to) filters.occurred_to = to
  return filters
}

function DetailItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="font-mono text-xs break-all text-slate-800">{children}</dd>
    </div>
  )
}

/**
 * Read-only audit log (`GET /admin/audit-events`, permission `audit.view`).
 * Each request is itself audited by the backend, so data is fetched only when
 * the page opens, when filters are applied, on "Refresh" and on "Load more".
 * Metadata is rendered as plain text, never as HTML.
 */
export function AuditLogPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const ids = { eventType: useId(), outcome: useId(), from: useId(), to: useId(), range: useId() }
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT)
  const [rangeError, setRangeError] = useState(false)
  const [filters, setFilters] = useState<AuditFilters>({})
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set())

  const query = useAuditEvents(filters)
  useRefreshSessionOnForbidden(query.error)
  const events = query.data?.pages.flatMap((page) => page.items) ?? []
  const language = i18n.resolvedLanguage

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (draft.from && draft.to && draft.from > draft.to) {
      setRangeError(true)
      return
    }
    setRangeError(false)
    setExpanded(new Set())
    setFilters(toFilters(draft))
  }

  function resetFilters() {
    setDraft(EMPTY_DRAFT)
    setRangeError(false)
    setExpanded(new Set())
    setFilters({})
  }

  function refresh() {
    setExpanded(new Set())
    void queryClient.resetQueries({ queryKey: adminQueryKeys.audit(filters), exact: true })
  }

  function toggle(eventId: string) {
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(eventId)) next.delete(eventId)
      else next.add(eventId)
      return next
    })
  }

  function eventLabel(code: string): string {
    const label = auditEventLabel(code)
    return label ? t(`audit.events.${label}`) : code
  }

  function target(event: AuditEvent): ReactNode {
    if (!event.target_type && !event.target_id) return '—'
    const type = event.target_type
    return (
      <>
        {type ? (
          <span className="block text-slate-700">
            {isAuditTargetType(type) ? t(`audit.targetTypes.${type}`) : type}
          </span>
        ) : null}
        {event.target_id ? (
          <span className="block font-mono text-xs break-all text-slate-500">{event.target_id}</span>
        ) : null}
      </>
    )
  }

  const columns = {
    time: t('admin.audit.columns.time'),
    event: t('admin.audit.columns.event'),
    outcome: t('admin.audit.columns.outcome'),
    actor: t('admin.audit.columns.actor'),
    target: t('admin.audit.columns.target'),
    details: t('admin.audit.columns.details'),
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader title={t('admin.audit.title')} subtitle={t('admin.audit.subtitle')} />

      <p className="flex gap-2 rounded-lg border border-brand-100 bg-brand-50 p-3 text-sm text-brand-900">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-brand-600" />
        {t('admin.audit.viewingRecorded')}
      </p>

      <form
        role="search"
        aria-label={t('admin.audit.title')}
        noValidate
        onSubmit={applyFilters}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-4"
      >
        <div className="space-y-1.5">
          <label htmlFor={ids.eventType} className={labelClassName}>
            {t('admin.audit.eventType')}
          </label>
          <select
            id={ids.eventType}
            value={draft.eventType}
            onChange={(event) => update('eventType', event.target.value)}
            className={inputClassName()}
          >
            <option value="">{t('admin.audit.allEventTypes')}</option>
            {AUDIT_EVENT_TYPES.map(([code, label]) => (
              <option key={code} value={code}>
                {t(`audit.events.${label}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.outcome} className={labelClassName}>
            {t('admin.audit.outcome')}
          </label>
          <select
            id={ids.outcome}
            value={draft.outcome}
            onChange={(event) => update('outcome', event.target.value as AuditOutcome | '')}
            className={inputClassName()}
          >
            <option value="">{t('admin.audit.allOutcomes')}</option>
            {AUDIT_OUTCOMES.map((code) => (
              <option key={code} value={code}>
                {t(`audit.outcomes.${code}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.from} className={labelClassName}>
            {t('admin.audit.from')}
          </label>
          <input
            id={ids.from}
            type="date"
            value={draft.from}
            onChange={(event) => update('from', event.target.value)}
            aria-invalid={rangeError ? true : undefined}
            aria-describedby={rangeError ? ids.range : undefined}
            className={inputClassName(rangeError)}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.to} className={labelClassName}>
            {t('admin.audit.to')}
          </label>
          <input
            id={ids.to}
            type="date"
            value={draft.to}
            onChange={(event) => update('to', event.target.value)}
            aria-invalid={rangeError ? true : undefined}
            aria-describedby={rangeError ? ids.range : undefined}
            className={inputClassName(rangeError)}
          />
        </div>
        {rangeError ? (
          <p id={ids.range} role="alert" className="text-sm text-red-700 sm:col-span-2 xl:col-span-4">
            {t('admin.audit.invalidRange')}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2 sm:col-span-2 xl:col-span-4">
          <button type="submit" className={primaryButtonClassName}>
            <Search aria-hidden="true" className="size-4" />
            {t('admin.applyFilters')}
          </button>
          <button type="button" onClick={resetFilters} className={secondaryButtonClassName}>
            <RotateCcw aria-hidden="true" className="size-4" />
            {t('admin.resetFilters')}
          </button>
          <button
            type="button"
            onClick={refresh}
            disabled={query.isFetching}
            className={`${secondaryButtonClassName} sm:ml-auto`}
          >
            <RefreshCw
              aria-hidden="true"
              className={`size-4 ${query.isFetching && !query.isFetchingNextPage ? 'animate-spin' : ''}`}
            />
            {t('common.refresh')}
          </button>
        </div>
      </form>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError && events.length === 0 ? (
        <AdminErrorState
          title={t('admin.audit.loadError')}
          error={query.error}
          onRetry={refresh}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('admin.audit.caption')}</caption>
              <thead className={TABLE_LAYOUTS.xl.head}>
                <tr>
                  {Object.values(columns).map((label) => (
                    <HeaderCell key={label}>{label}</HeaderCell>
                  ))}
                </tr>
              </thead>
              <tbody className={TABLE_LAYOUTS.xl.body}>
                {events.map((event) => {
                  const isOpen = expanded.has(event.event_id)
                  const detailsId = `audit-details-${event.event_id}`
                  const label = auditEventLabel(event.event_type)
                  return (
                    <Fragment key={event.event_id}>
                      <tr className={TABLE_LAYOUTS.xl.row}>
                        <Cell layout="xl" label={columns.time}>
                          <time
                            dateTime={event.occurred_at}
                            title={new Date(event.occurred_at).toISOString()}
                            className="text-slate-700 xl:whitespace-nowrap"
                          >
                            {formatDateTime(event.occurred_at, language, {
                              dateStyle: 'medium',
                              timeStyle: 'medium',
                            })}
                          </time>
                        </Cell>
                        <Cell layout="xl" label={columns.event}>
                          <span className="block font-medium text-slate-900">
                            {eventLabel(event.event_type)}
                          </span>
                          {label ? (
                            <span className="block font-mono text-xs text-slate-500">
                              {event.event_type}
                            </span>
                          ) : null}
                        </Cell>
                        <Cell layout="xl" label={columns.outcome}>
                          <OutcomeBadge outcome={event.outcome} />
                        </Cell>
                        <Cell layout="xl" label={columns.actor}>
                          {event.actor ? (
                            <>
                              <span className="block text-slate-800">{event.actor.display_name}</span>
                              <span className="block font-mono text-xs text-slate-500">
                                {event.actor.login_id}
                              </span>
                            </>
                          ) : (
                            <span className="text-slate-500">{t('admin.audit.noActor')}</span>
                          )}
                        </Cell>
                        <Cell layout="xl" label={columns.target}>{target(event)}</Cell>
                        <Cell layout="xl" label={columns.details}>
                          <button
                            type="button"
                            onClick={() => toggle(event.event_id)}
                            aria-expanded={isOpen}
                            aria-controls={detailsId}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-brand-700 xl:whitespace-nowrap hover:bg-brand-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                          >
                            <ChevronDown
                              aria-hidden="true"
                              className={`size-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                            />
                            {isOpen ? t('admin.audit.hideDetails') : t('admin.audit.showDetails')}
                          </button>
                        </Cell>
                      </tr>
                      {isOpen ? (
                        <tr id={detailsId} className={TABLE_LAYOUTS.xl.detailRow}>
                          <td colSpan={6} className={TABLE_LAYOUTS.xl.detailCell}>
                            <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
                              <DetailItem label={t('admin.audit.details.eventId')}>
                                {event.event_id}
                              </DetailItem>
                              <DetailItem label={t('admin.audit.details.requestId')}>
                                {event.request_id ?? '—'}
                              </DetailItem>
                              <DetailItem label={t('admin.audit.details.sourceIp')}>
                                {event.source_ip ?? '—'}
                              </DetailItem>
                              <DetailItem label={t('admin.audit.details.userAgent')}>
                                {event.user_agent ?? '—'}
                              </DetailItem>
                            </dl>
                            {event.metadata && Object.keys(event.metadata).length > 0 ? (
                              <div className="mt-3">
                                <p className="text-xs font-medium text-slate-500">
                                  {t('admin.audit.details.metadata')}
                                </p>
                                <dl className="mt-1 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                                  {Object.entries(event.metadata).map(([key, value]) => (
                                    <DetailItem key={key} label={key}>
                                      {typeof value === 'string' ? value : JSON.stringify(value)}
                                    </DetailItem>
                                  ))}
                                </dl>
                              </div>
                            ) : null}
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
            {events.length === 0 ? (
              <p className="p-6 text-center text-slate-600">{t('admin.audit.empty')}</p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-slate-600">
              <p role="status" aria-live="polite">
                {t('admin.audit.count', { count: events.length })}
              </p>
              {query.dataUpdatedAt ? (
                <p className="text-xs text-slate-500">
                  {t('admin.audit.loadedAt', {
                    time: formatDateTime(new Date(query.dataUpdatedAt).toISOString(), language, {
                      timeStyle: 'medium',
                    }),
                  })}
                </p>
              ) : null}
            </div>
            {query.hasNextPage ? (
              <button
                type="button"
                onClick={() => void query.fetchNextPage()}
                disabled={query.isFetchingNextPage}
                className={secondaryButtonClassName}
              >
                {query.isFetchingNextPage ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : null}
                {t('common.loadMore')}
              </button>
            ) : null}
          </div>

          {query.isFetchNextPageError ? (
            <AdminErrorState
              title={t('admin.audit.loadError')}
              error={query.error}
              onRetry={() => void query.fetchNextPage()}
              isRetrying={query.isFetchingNextPage}
            />
          ) : null}
        </div>
      )}
    </div>
  )
}
