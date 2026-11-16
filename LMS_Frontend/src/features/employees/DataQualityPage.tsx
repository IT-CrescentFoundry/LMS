import { ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'

import { LoadingState } from '../../components/LoadingState'
import { formatDate } from '../../lib/format'
import { DATA_QUALITY_CHECKS, isDataQualityCheck, type DataQualityCheck } from '../../types/employee'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { Cell, HeaderCell } from '../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { ListFooter } from '../organisation/ListParts'
import { InfoNote } from '../organisation/OrgParts'
import { useDataQuality } from './employeeQueries'
import { AsOfControl, EmployeeErrorState, EmploymentStatusBadge, OrgPath } from './EmployeeParts'
import { CHECK_TAB } from './sections'

const LAYOUT = TABLE_LAYOUTS.xl
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

/**
 * Data quality (`employees.manage`): the eight backend checks with their counts
 * on a date, and the employees failing one check. Strictly a report - every rule
 * is evaluated by the server, and nothing is corrected from here. Each employee
 * links to the profile section where the record is fixed with the normal,
 * audited workflows.
 */
export function DataQualityPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [params, setParams] = useSearchParams()
  const asOfParam = params.get('as_of') ?? ''
  const asOf = ISO_DATE.test(asOfParam) ? asOfParam : undefined
  const checkParam = params.get('check')
  const check: DataQualityCheck | null = isDataQualityCheck(checkParam) ? checkParam : null
  const canHistory = useHasPermission(PERMISSIONS.EMPLOYEES_HISTORY_VIEW)
  const query = useDataQuality(asOf, check)
  useRefreshSessionOnForbidden(query.error)

  function update(key: 'as_of' | 'check', value: string | null) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: key === 'as_of' })
  }

  const first = query.data?.pages[0]
  const items = query.data?.pages.flatMap((page) => page.items) ?? []
  // While another check or date loads, the previous counts stay visible, but the
  // list is never shown under the wrong heading (it could claim "no issues").
  const listStale = query.isPlaceholderData || (first !== undefined && first.check !== check)

  function profileLink(employeeId: string, chosen: DataQualityCheck): string {
    const target = CHECK_TAB[chosen]
    const tab = target.needsHistory && !canHistory ? '' : target.tab
    return `/employees/${employeeId}${tab ? `/${tab}` : ''}${asOf ? `?as_of=${asOf}` : ''}`
  }

  const columns = {
    employee: t('emp.directory.columns.employee'),
    status: t('emp.directory.columns.status'),
    organisation: t('emp.directory.columns.organisation'),
    designation: t('emp.directory.columns.designation'),
    location: t('emp.directory.columns.location'),
    review: t('emp.dataQuality.columns.review'),
  }
  const dash = <span className="text-slate-500">—</span>

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{t('emp.dataQuality.title')}</h1>
          <p className="max-w-3xl text-slate-600">{t('emp.dataQuality.subtitle')}</p>
        </div>
        <AsOfControl value={asOf ?? ''} onChange={(value) => update('as_of', value || null)} />
      </header>
      <InfoNote>{t('emp.dataQuality.readOnlyNote')}</InfoNote>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError && !first ? (
        <EmployeeErrorState
          title={t('emp.dataQuality.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : first ? (
        <>
          <section aria-labelledby="dq-checks" className="space-y-3">
            <h2 id="dq-checks" className="text-lg font-semibold text-slate-900">
              {t('emp.dataQuality.checksTitle', { date: formatDate(first.as_of, language) })}
            </h2>
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {DATA_QUALITY_CHECKS.map((code) => {
                const count = first.counts[code]
                const selected = code === check
                return (
                  <li key={code} className="min-w-0">
                    <button
                      type="button"
                      aria-pressed={selected}
                      data-check={code}
                      onClick={() => update('check', selected ? null : code)}
                      className={`flex h-full w-full flex-col gap-2 rounded-xl border p-4 text-left shadow-sm focus:ring-2 focus:ring-brand-500 focus:outline-none ${
                        selected
                          ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <span className="flex items-start justify-between gap-3">
                        <span className="min-w-0 font-semibold break-words text-slate-900">
                          {t(`emp.dataQuality.checks.${code}.title`)}
                        </span>
                        <span
                          className={`shrink-0 rounded-full px-2.5 py-0.5 text-sm font-semibold ${
                            count ? 'bg-amber-100 text-amber-900' : 'bg-emerald-50 text-emerald-800'
                          }`}
                          data-count
                        >
                          {count === undefined ? '—' : count}
                        </span>
                      </span>
                      <span className="text-sm break-words text-slate-600">
                        {t(`emp.dataQuality.checks.${code}.description`)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>

          {check === null ? (
            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
              {t('emp.dataQuality.chooseCheck')}
            </p>
          ) : (
            <section aria-labelledby="dq-list" aria-busy={listStale} className="space-y-4">
              <h2 id="dq-list" className="text-lg font-semibold text-slate-900">
                {t('emp.dataQuality.listTitle', {
                  check: t(`emp.dataQuality.checks.${check}.title`),
                  count: first.counts[check] ?? items.length,
                })}
              </h2>
              {listStale ? (
                <LoadingState />
              ) : (
              <>
              <div className={TABLE_CONTAINER}>
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">{t(`emp.dataQuality.checks.${check}.title`)}</caption>
                  <thead className={LAYOUT.head}>
                    <tr>
                      {Object.values(columns).map((label) => (
                        <HeaderCell key={label}>{label}</HeaderCell>
                      ))}
                    </tr>
                  </thead>
                  <tbody className={LAYOUT.body}>
                    {items.map((employee) => (
                      <tr key={employee.public_id} className={LAYOUT.row}>
                        <Cell label={columns.employee} layout="xl">
                          <span className="font-medium text-slate-900">
                            <span className="font-mono">{employee.employee_code}</span> · {employee.full_name}
                          </span>
                        </Cell>
                        <Cell label={columns.status} layout="xl">
                          <EmploymentStatusBadge status={employee.employment_status} />
                        </Cell>
                        <Cell label={columns.organisation} layout="xl">
                          <OrgPath path={employee.path} unit={employee.primary_unit} />
                        </Cell>
                        <Cell label={columns.designation} layout="xl">
                          {employee.designation?.name ?? dash}
                        </Cell>
                        <Cell label={columns.location} layout="xl">
                          {employee.location?.name ?? dash}
                        </Cell>
                        <Cell label={columns.review} layout="xl">
                          <Link
                            to={profileLink(employee.public_id, check)}
                            aria-label={t('emp.dataQuality.reviewFor', { code: employee.employee_code })}
                            className="inline-flex items-center gap-1 rounded font-medium text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
                          >
                            {t('emp.dataQuality.review')}
                            <ChevronRight aria-hidden="true" className="size-4" />
                          </Link>
                        </Cell>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {items.length === 0 ? (
                  <p className="p-6 text-center text-slate-600">{t('emp.dataQuality.noIssues')}</p>
                ) : null}
              </div>
              <ListFooter
                countText={t('emp.dataQuality.count', { count: items.length })}
                hasMore={Boolean(query.hasNextPage)}
                loadingMore={query.isFetchingNextPage}
                onLoadMore={() => void query.fetchNextPage()}
              />
              {query.isFetchNextPageError ? (
                <EmployeeErrorState
                  title={t('emp.dataQuality.loadError')}
                  error={query.error}
                  onRetry={() => void query.fetchNextPage()}
                  isRetrying={query.isFetchingNextPage}
                />
              ) : null}
              </>
              )}
            </section>
          )}
        </>
      ) : null}
    </div>
  )
}
