import { Download } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { importService, saveDownload } from '../../services/importService'
import {
  ISSUE_SEVERITIES,
  isRowOutcome,
  ROW_OUTCOMES,
  type ImportIssue,
  type ImportJob,
  type ImportRow,
  type IssueSeverity,
  type RowDecision,
  type RowOutcome,
} from '../../types/imports'
import { ListFooter } from '../organisation/ListParts'
import { SelectField, TextAreaField } from '../organisation/OrgParts'
import { ActionError, CountTile, ImportErrorState, RowOutcomeBadge, SeverityBadge } from './ImportParts'
import { formatCount, useFieldLabel, useIssueMessage, useSectionLabel } from './importLabels'
import { useImportIssues, useImportRows, useJobMutation } from './importQueries'
import { shownFields } from './mapping'

/**
 * Validation results of a job: counts, then the staged rows (with their issues
 * and the decisions that can be taken on them) and a flat issue list. Cell
 * values are shown as the server normalised them, for mapped columns only.
 */
export function ValidationResults({
  job,
  canDecide,
  onReload,
}: {
  job: ImportJob
  canDecide: boolean
  onReload: () => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [tab, setTab] = useState<'rows' | 'issues'>('rows')
  const [downloadError, setDownloadError] = useState<unknown>(null)
  const counts = job.counts
  const blocking = counts.blocking_errors ?? 0
  const undecided = counts.undecided_duplicates ?? 0

  async function downloadReport() {
    setDownloadError(null)
    try {
      saveDownload(await importService.downloadErrorReport(job.public_id))
    } catch (error) {
      setDownloadError(error)
    }
  }

  return (
    <section aria-labelledby="imp-results" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 id="imp-results" className="text-lg font-semibold text-slate-900">
          {t('imp.results.title')}
        </h2>
        <button type="button" className={secondaryButtonClassName} onClick={() => void downloadReport()}>
          <Download aria-hidden="true" className="size-4" />
          {t('imp.actions.downloadErrorReport')}
        </button>
      </div>
      {downloadError ? <ActionError error={downloadError} /> : null}

      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <CountTile label={t('imp.results.counts.rows')} value={formatCount(counts.rows, language)} />
        <CountTile
          label={t('imp.results.counts.importable')}
          value={formatCount(counts.importable, language)}
          tone="emerald"
        />
        <CountTile
          label={t('imp.results.counts.blocking')}
          value={formatCount(blocking, language)}
          tone={blocking ? 'red' : 'slate'}
        />
        <CountTile
          label={t('imp.results.counts.undecided')}
          value={formatCount(undecided, language)}
          tone={undecided ? 'amber' : 'slate'}
        />
        <CountTile label={t('imp.results.counts.warnings')} value={formatCount(counts.warnings, language)} />
      </dl>
      <p className="text-sm text-slate-600">
        {t('imp.results.skippedNote', {
          skipped: formatCount(counts.skipped_rows ?? 0, language),
          blank: formatCount(counts.skipped_blank ?? 0, language),
          headers: formatCount(counts.skipped_repeated_header ?? 0, language),
        })}
      </p>

      <div role="tablist" aria-label={t('imp.results.tabsLabel')} className="flex flex-wrap gap-2">
        {(['rows', 'issues'] as const).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none ${
              tab === name ? 'bg-brand-700 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50'
            }`}
          >
            {t(`imp.results.tabs.${name}`)}
          </button>
        ))}
      </div>
      {tab === 'rows' ? (
        <RowList job={job} canDecide={canDecide} onReload={onReload} />
      ) : (
        <IssueList jobId={job.public_id} />
      )}
    </section>
  )
}

function RowList({ job, canDecide, onReload }: { job: ImportJob; canDecide: boolean; onReload: () => void }) {
  const { t } = useTranslation()
  const sectionLabel = useSectionLabel()
  const [section, setSection] = useState('')
  const [outcome, setOutcome] = useState<RowOutcome | ''>('')
  const rows = useImportRows(
    job.public_id,
    { section: section || undefined, outcome: outcome || undefined },
    true,
  )
  const [deciding, setDeciding] = useState<{ row: ImportRow; decision: RowDecision } | null>(null)
  const undo = useJobMutation((row: ImportRow) =>
    importService.decideRow(job.public_id, row.id, { version: job.version, decision: null }),
  )
  const items = rows.data?.pages.flatMap((page) => page.items) ?? []
  const sections = [...new Set(job.column_mapping.map((item) => item.section))]

  return (
    <div className="space-y-4" role="tabpanel">
      <div className="grid gap-3 sm:grid-cols-2 lg:w-2/3">
        <SelectField
          label={t('imp.results.sectionFilter')}
          value={section}
          onChange={setSection}
          emptyLabel={t('imp.results.allSections')}
          options={sections.map((value) => ({ value, label: sectionLabel(value) }))}
        />
        <SelectField
          label={t('imp.results.outcomeFilter')}
          value={outcome}
          onChange={(value) => setOutcome(isRowOutcome(value) ? value : '')}
          emptyLabel={t('imp.results.allOutcomes')}
          options={ROW_OUTCOMES.map((value) => ({ value, label: t(`imp.outcomes.${value}`) }))}
        />
      </div>
      {undo.isError ? <ActionError error={undo.error} onReload={onReload} /> : null}
      {rows.isPending ? (
        <LoadingState />
      ) : rows.isError && items.length === 0 ? (
        <ImportErrorState
          title={t('imp.results.rowsLoadError')}
          error={rows.error}
          onRetry={() => void rows.refetch()}
          isRetrying={rows.isFetching}
        />
      ) : (
        <>
          <ul className="space-y-3" aria-busy={rows.isPlaceholderData}>
            {items.map((row) => (
              <RowCard
                key={row.id}
                row={row}
                canDecide={canDecide}
                busy={undo.isPending}
                onDecide={(decision) => setDeciding({ row, decision })}
                onUndo={() => undo.mutate(row)}
              />
            ))}
          </ul>
          {items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
              {t('imp.results.noRows')}
            </p>
          ) : null}
          <ListFooter
            countText={t('imp.results.rowCount', { count: items.length })}
            hasMore={Boolean(rows.hasNextPage)}
            loadingMore={rows.isFetchingNextPage}
            onLoadMore={() => void rows.fetchNextPage()}
          />
        </>
      )}
      {deciding ? (
        <DecisionDialog
          job={job}
          row={deciding.row}
          decision={deciding.decision}
          onClose={() => setDeciding(null)}
          onReload={onReload}
        />
      ) : null}
    </div>
  )
}

function RowCard({
  row,
  canDecide,
  busy,
  onDecide,
  onUndo,
}: {
  row: ImportRow
  canDecide: boolean
  busy: boolean
  onDecide: (decision: RowDecision) => void
  onUndo: () => void
}) {
  const { t } = useTranslation()
  const sectionLabel = useSectionLabel()
  const fieldLabel = useFieldLabel()
  const issueMessage = useIssueMessage()
  const needsDecision = row.issues.some((issue) => issue.params?.requires_decision === true)
  const ordered = shownFields(row.values)
  const text = (value: unknown) => (value === null || value === undefined || value === '' ? '—' : String(value))

  return (
    <li
      className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      data-row={`${row.sheet}!${row.row_number}`}
      data-outcome={row.outcome}
    >
      <div className="flex flex-wrap items-center gap-2">
        <RowOutcomeBadge outcome={row.outcome} />
        <span className="text-sm font-medium text-slate-900">
          {t('imp.results.rowRef', { sheet: row.sheet, row: row.row_number })}
        </span>
        <span className="text-sm text-slate-600">· {sectionLabel(row.section)}</span>
        {row.decision ? (
          <span className="text-sm text-amber-900">
            · {t(`imp.decisions.${row.decision}`)}
            {row.decision_reason ? `: ${row.decision_reason}` : ''}
          </span>
        ) : null}
      </div>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 xl:grid-cols-3">
        {ordered.map((field) => (
          <div key={field} className="flex min-w-0 gap-2">
            <dt className="shrink-0 text-slate-500">{fieldLabel(field)}</dt>
            <dd className="min-w-0 break-words text-slate-900">
              {text(row.values[field] ?? row.source[field])}
              {row.source[field] !== undefined && row.source[field] !== row.values[field] ? (
                <span className="text-slate-500"> ({t('imp.results.fromFile', { value: text(row.source[field]) })})</span>
              ) : null}
            </dd>
          </div>
        ))}
      </dl>
      {row.changes && Object.keys(row.changes).length > 0 ? (
        <div className="rounded-lg bg-brand-50 p-3 text-sm text-brand-900">
          <p className="font-medium">{t('imp.results.changesTitle')}</p>
          <ul className="list-disc pl-5">
            {Object.entries(row.changes).map(([field, change]) => (
              <li key={field}>
                {t('imp.results.change', { field: fieldLabel(field), from: text(change.from), to: text(change.to) })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {row.issues.length > 0 ? (
        <ul className="space-y-1">
          {row.issues.map((issue) => (
            <li key={issue.id} className="flex flex-wrap items-start gap-2 text-sm">
              <SeverityBadge severity={issue.severity} />
              <span className="min-w-0 break-words text-slate-800">
                {issueMessage(issue)}
                {issue.field ? <span className="text-slate-500"> · {fieldLabel(issue.field)}</span> : null}
                {issue.column ? <span className="text-slate-500"> · {t('imp.results.columnRef', { column: issue.column })}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {canDecide ? (
        <div className="flex flex-wrap gap-2">
          {row.decision ? (
            <button type="button" className={secondaryButtonClassName} disabled={busy} onClick={onUndo}>
              {t('imp.actions.undoDecision')}
            </button>
          ) : (
            <>
              {needsDecision ? (
                <button type="button" className={secondaryButtonClassName} onClick={() => onDecide('distinct')}>
                  {t('imp.actions.markDistinct')}
                </button>
              ) : null}
              {row.outcome !== 'unchanged' ? (
                <button type="button" className={secondaryButtonClassName} onClick={() => onDecide('skip')}>
                  {t('imp.actions.skipRow')}
                </button>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </li>
  )
}

function DecisionDialog({
  job,
  row,
  decision,
  onClose,
  onReload,
}: {
  job: ImportJob
  row: ImportRow
  decision: RowDecision
  onClose: () => void
  onReload: () => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  const [touched, setTouched] = useState(false)
  const mutation = useJobMutation(() =>
    importService.decideRow(job.public_id, row.id, {
      version: job.version,
      decision,
      reason: reason.trim() || null,
    }),
  )
  const reasonMissing = decision === 'skip' && reason.trim() === ''

  function submit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (reasonMissing) return
    mutation.mutate(undefined, { onSuccess: onClose })
  }

  return (
    <Modal
      title={t(`imp.decisionDialog.${decision}.title`)}
      description={t(`imp.decisionDialog.${decision}.description`, { sheet: row.sheet, row: row.row_number })}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <TextAreaField
          label={decision === 'skip' ? t('imp.decisionDialog.reasonRequired') : t('imp.decisionDialog.reason')}
          value={reason}
          onChange={setReason}
          maxLength={500}
          required={decision === 'skip'}
          error={touched && reasonMissing ? t('imp.decisionDialog.reasonMissing') : undefined}
        />
        <p className="text-sm text-slate-600">{t('imp.decisionDialog.revalidateNote')}</p>
        {mutation.isError ? (
          <ActionError
            error={mutation.error}
            onReload={() => {
              onReload()
              onClose()
            }}
          />
        ) : null}
        <div className="flex flex-wrap justify-end gap-3">
          <button type="button" className={secondaryButtonClassName} onClick={onClose} disabled={mutation.isPending}>
            {t('imp.actions.cancel')}
          </button>
          <button type="submit" className={primaryButtonClassName} disabled={mutation.isPending}>
            {t(`imp.decisionDialog.${decision}.confirm`)}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function IssueList({ jobId }: { jobId: string }) {
  const { t } = useTranslation()
  const issueMessage = useIssueMessage()
  const fieldLabel = useFieldLabel()
  const [severity, setSeverity] = useState<IssueSeverity | ''>('')
  const issues = useImportIssues(jobId, { severity: severity || undefined }, true)
  const items: ImportIssue[] = issues.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div className="space-y-4" role="tabpanel">
      <div className="sm:w-64">
        <SelectField
          label={t('imp.results.severityFilter')}
          value={severity}
          onChange={(value) => setSeverity(value === 'error' || value === 'warning' ? value : '')}
          emptyLabel={t('imp.results.allSeverities')}
          options={ISSUE_SEVERITIES.map((value) => ({ value, label: t(`imp.severity.${value}`) }))}
        />
      </div>
      {issues.isPending ? (
        <LoadingState />
      ) : issues.isError && items.length === 0 ? (
        <ImportErrorState
          title={t('imp.results.issuesLoadError')}
          error={issues.error}
          onRetry={() => void issues.refetch()}
          isRetrying={issues.isFetching}
        />
      ) : (
        <>
          <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-sm" aria-busy={issues.isPlaceholderData}>
            {items.map((issue) => (
              <li key={issue.id} className="flex flex-wrap items-start gap-2 p-3 text-sm" data-issue={issue.code}>
                <SeverityBadge severity={issue.severity} />
                <span className="font-medium text-slate-900">
                  {issue.sheet && issue.row_number
                    ? t('imp.results.rowRef', { sheet: issue.sheet, row: issue.row_number })
                    : t('imp.results.fileLevel')}
                  {issue.column ? ` · ${t('imp.results.columnRef', { column: issue.column })}` : ''}
                </span>
                <span className="min-w-0 basis-full break-words text-slate-800 sm:basis-auto">
                  {issueMessage(issue)}
                  {issue.field ? <span className="text-slate-500"> · {fieldLabel(issue.field)}</span> : null}
                  {issue.source_value ? (
                    <span className="text-slate-500"> · {t('imp.results.fromFile', { value: issue.source_value })}</span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
          {items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
              {t('imp.results.noIssues')}
            </p>
          ) : null}
          <ListFooter
            countText={t('imp.results.issueCount', { count: items.length })}
            hasMore={Boolean(issues.hasNextPage)}
            loadingMore={issues.isFetchingNextPage}
            onLoadMore={() => void issues.fetchNextPage()}
          />
        </>
      )}
    </div>
  )
}
