import { ChevronRight, FileUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDateTime } from '../../lib/format'
import { IMPORT_STATUSES, isImportStatus, type ImportStatus } from '../../types/imports'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { Cell, HeaderCell } from '../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useAuth } from '../auth/authContext'
import { hasAnyPermission, IMPORT_RUN_PERMISSIONS } from '../auth/permissions'
import { ListFooter } from '../organisation/ListParts'
import { InfoNote, SelectField } from '../organisation/OrgParts'
import { ImportErrorState, ImportStatusBadge } from './ImportParts'
import { formatCount } from './importLabels'
import { useImportJobs, useValueMappings } from './importQueries'

const LAYOUT = TABLE_LAYOUTS.xl
/** Open jobs that need someone to act, shown as tiles above the history. */
const ATTENTION = ['mapping_required', 'validation_failed', 'ready_for_approval'] as const satisfies readonly ImportStatus[]

/**
 * Import Control Room overview (`imports.view`): what needs attention, then the
 * full import history (newest first) with a status filter. Every job opens its
 * own page; nothing is changed from here.
 */
export function ImportsOverviewPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [params, setParams] = useSearchParams()
  const statusParam = params.get('status')
  const status = isImportStatus(statusParam) ? statusParam : undefined
  const canRun = hasAnyPermission(useAuth().user, IMPORT_RUN_PERMISSIONS)
  const jobs = useImportJobs({ status })
  const pending = useValueMappings({ status: 'pending' })
  useRefreshSessionOnForbidden(jobs.error)

  const items = jobs.data?.pages.flatMap((page) => page.items) ?? []
  const pendingCount = pending.data?.pages[0]?.items.length
  const pendingMore = Boolean(pending.data?.pages[0]?.next_cursor)

  function setStatus(value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set('status', value)
    else next.delete('status')
    setParams(next, { replace: true })
  }

  const columns = {
    file: t('imp.history.columns.file'),
    status: t('imp.history.columns.status'),
    rows: t('imp.history.columns.rows'),
    uploaded: t('imp.history.columns.uploaded'),
    by: t('imp.history.columns.by'),
    open: t('imp.history.columns.open'),
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{t('imp.overview.title')}</h1>
          <p className="max-w-3xl text-slate-600">{t('imp.overview.subtitle')}</p>
        </div>
        {canRun ? (
          <Link to="/imports/new" className={primaryButtonClassName}>
            <FileUp aria-hidden="true" className="size-4" />
            {t('imp.actions.newImport')}
          </Link>
        ) : null}
      </header>
      <InfoNote>{t('imp.overview.safetyNote')}</InfoNote>

      <section aria-labelledby="imp-attention" className="space-y-3">
        <h2 id="imp-attention" className="text-lg font-semibold text-slate-900">
          {t('imp.overview.attentionTitle')}
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {ATTENTION.map((code) => (
            <li key={code} className="min-w-0">
              <button
                type="button"
                aria-pressed={status === code}
                onClick={() => setStatus(status === code ? '' : code)}
                className={`flex h-full w-full flex-col gap-1 rounded-xl border p-4 text-left shadow-sm focus:ring-2 focus:ring-brand-500 focus:outline-none ${
                  status === code
                    ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <span className="font-semibold break-words text-slate-900">{t(`imp.status.${code}`)}</span>
                <span className="text-sm break-words text-slate-600">{t(`imp.overview.attention.${code}`)}</span>
              </button>
            </li>
          ))}
          <li className="min-w-0">
            <Link
              to="/imports/mappings"
              className="flex h-full w-full flex-col gap-1 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <span className="flex items-start justify-between gap-3">
                <span className="font-semibold break-words text-slate-900">{t('imp.overview.pendingMappings')}</span>
                <span
                  data-count
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-sm font-semibold ${
                    pendingCount ? 'bg-amber-100 text-amber-900' : 'bg-emerald-50 text-emerald-800'
                  }`}
                >
                  {pendingCount === undefined ? '—' : `${pendingCount}${pendingMore ? '+' : ''}`}
                </span>
              </span>
              <span className="text-sm break-words text-slate-600">{t('imp.overview.pendingMappingsHint')}</span>
            </Link>
          </li>
        </ul>
      </section>

      <section aria-labelledby="imp-history" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="imp-history" className="text-lg font-semibold text-slate-900">
            {t('imp.history.title')}
          </h2>
          <div className="w-full sm:w-64">
            <SelectField
              label={t('imp.history.statusFilter')}
              value={status ?? ''}
              onChange={setStatus}
              emptyLabel={t('imp.history.allStatuses')}
              options={IMPORT_STATUSES.map((value) => ({ value, label: t(`imp.status.${value}`) }))}
            />
          </div>
        </div>
        {jobs.isPending ? (
          <LoadingState />
        ) : jobs.isError && items.length === 0 ? (
          <ImportErrorState
            title={t('imp.history.loadError')}
            error={jobs.error}
            onRetry={() => void jobs.refetch()}
            isRetrying={jobs.isFetching}
          />
        ) : (
          <>
            <div className={TABLE_CONTAINER}>
              <table className="w-full text-left text-sm">
                <caption className="sr-only">{t('imp.history.title')}</caption>
                <thead className={LAYOUT.head}>
                  <tr>
                    {Object.values(columns).map((label) => (
                      <HeaderCell key={label}>{label}</HeaderCell>
                    ))}
                  </tr>
                </thead>
                <tbody className={LAYOUT.body}>
                  {items.map((job) => (
                    <tr key={job.public_id} className={LAYOUT.row} data-job={job.public_id}>
                      <Cell label={columns.file} layout="xl">
                        <span className="font-medium break-all text-slate-900">{job.original_filename}</span>
                        <span className="block text-xs text-slate-500">
                          {t('imp.history.profile', { code: job.profile_code, version: job.profile_version })}
                        </span>
                      </Cell>
                      <Cell label={columns.status} layout="xl">
                        <ImportStatusBadge status={job.status} />
                      </Cell>
                      <Cell label={columns.rows} layout="xl">
                        {formatCount(job.counts.rows, language)}
                      </Cell>
                      <Cell label={columns.uploaded} layout="xl">
                        {formatDateTime(job.uploaded_at, language)}
                      </Cell>
                      <Cell label={columns.by} layout="xl">
                        {job.uploaded_by?.display_name ?? '—'}
                      </Cell>
                      <Cell label={columns.open} layout="xl">
                        <Link
                          to={`/imports/${job.public_id}`}
                          aria-label={t('imp.history.openFor', { file: job.original_filename })}
                          className="inline-flex items-center gap-1 rounded font-medium text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
                        >
                          {t('imp.history.open')}
                          <ChevronRight aria-hidden="true" className="size-4" />
                        </Link>
                      </Cell>
                    </tr>
                  ))}
                </tbody>
              </table>
              {items.length === 0 ? <p className="p-6 text-center text-slate-600">{t('imp.history.empty')}</p> : null}
            </div>
            <ListFooter
              countText={t('imp.history.count', { count: items.length })}
              hasMore={Boolean(jobs.hasNextPage)}
              loadingMore={jobs.isFetchingNextPage}
              onLoadMore={() => void jobs.fetchNextPage()}
            />
          </>
        )}
      </section>
    </div>
  )
}
