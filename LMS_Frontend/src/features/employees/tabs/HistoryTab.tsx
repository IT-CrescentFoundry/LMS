import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { formatDateTime } from '../../../lib/format'
import type { AuditEvent } from '../../../types/admin'
import { employeeEventLabel } from '../../../types/employee'
import { ListFooter } from '../../organisation/ListParts'
import { useEmployeeHistory } from '../employeeQueries'
import { useProfile } from '../profileContext'
import { EmployeeErrorState } from '../EmployeeParts'

/**
 * Change history: the audit events that target this employee, newest first
 * (`employees.history.view`). Network details are never part of this view; they
 * stay in the audit log (`audit.view`).
 */
export function HistoryTab() {
  const { t } = useTranslation()
  const { employee } = useProfile()
  const query = useEmployeeHistory(employee.public_id)
  const events = query.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <section aria-labelledby="emp-history" className="space-y-4">
      <h2 id="emp-history" className="text-lg font-semibold text-slate-900">
        {t('emp.history.title')}
      </h2>
      {query.isPending ? (
        <LoadingState />
      ) : query.isError && events.length === 0 ? (
        <EmployeeErrorState
          title={t('emp.history.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <>
          {events.length === 0 ? (
            <p className="text-sm text-slate-600">{t('emp.history.empty')}</p>
          ) : (
            <ol className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-sm">
              {events.map((event) => (
                <li key={event.event_id} className="p-4">
                  <EventLine event={event} />
                </li>
              ))}
            </ol>
          )}
          <ListFooter
            countText={t('emp.history.count', { count: events.length })}
            hasMore={Boolean(query.hasNextPage)}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
          />
        </>
      )}
    </section>
  )
}

/** One audit event: translated type, who and when, the reason, and the raw details. */
export function EventLine({ event }: { event: AuditEvent }) {
  const { t, i18n } = useTranslation()
  const label = employeeEventLabel(event.event_type)
  const metadata = event.metadata ?? {}
  const reason = typeof metadata.reason === 'string' && metadata.reason ? metadata.reason : null
  const login = typeof metadata.login_id === 'string' ? metadata.login_id : null
  return (
    <div className="space-y-1 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium text-slate-900">
          {label ? t(`emp.history.events.${label}`) : event.event_type}
          {login ? <span className="ml-2 font-mono text-slate-700">{login}</span> : null}
        </p>
        <time dateTime={event.occurred_at} className="text-xs text-slate-600">
          {formatDateTime(event.occurred_at, i18n.resolvedLanguage, { dateStyle: 'medium', timeStyle: 'short' })}
        </time>
      </div>
      <p className="text-slate-700">
        {event.actor
          ? t('emp.history.by', { name: event.actor.display_name, login: event.actor.login_id })
          : t('emp.history.bySystem')}
      </p>
      {reason ? <p className="text-slate-700">{t('emp.history.reason', { reason })}</p> : null}
      {Object.keys(metadata).length > 0 ? (
        <details className="text-xs text-slate-600">
          <summary className="cursor-pointer rounded focus:ring-2 focus:ring-brand-500 focus:outline-none">
            {t('emp.history.details')}
          </summary>
          <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 font-mono whitespace-pre-wrap break-words">
            {JSON.stringify(metadata, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  )
}
