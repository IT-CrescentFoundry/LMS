import { CircleCheck, LoaderCircle, TriangleAlert } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { formatDateTime } from '../../lib/format'
import { importService } from '../../services/importService'
import { isTerminal, type ImportJob, type ImportProfile } from '../../types/imports'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { CheckboxField, InfoNote } from '../organisation/OrgParts'
import { ActionError, CountTile, ImportErrorState, ImportStatusBadge, StepIndicator } from './ImportParts'
import { currentStep, formatBytes, formatCount, useSectionLabel } from './importLabels'
import { useImportJob, useImportProfiles, useJobMutation } from './importQueries'
import { MappingEditor } from './MappingEditor'
import { ValidationResults } from './ValidationResults'

const VALIDATED = new Set(['validation_failed', 'ready_for_approval', 'committing', 'completed', 'completed_with_skips', 'failed'])

/**
 * One import job: file facts, the workflow step, then - depending on the state -
 * the column mapping, validation (a dry run), the validation results with row
 * decisions, the explicit approval, and the result. Every action is checked by
 * the server against the job's current version and state.
 */
export function ImportJobPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const { jobId = '' } = useParams()
  const job = useImportJob(jobId)
  const profiles = useImportProfiles()
  useRefreshSessionOnForbidden(job.error)
  const reload = useCallback(() => void job.refetch(), [job])

  if (job.isPending || profiles.isPending) return <LoadingState />
  if (job.isError) {
    return (
      <ImportErrorState
        title={t('imp.job.loadError')}
        error={job.error}
        onRetry={() => void job.refetch()}
        isRetrying={job.isFetching}
      />
    )
  }
  const data = job.data
  const profile = profiles.data?.find((item) => item.code === data.profile_code)
  return (
    <JobView
      key={`${data.public_id}-${data.version}`}
      job={data}
      profile={profile}
      language={language}
      onReload={reload}
    />
  )
}

function JobView({
  job,
  profile,
  language,
  onReload,
}: {
  job: ImportJob
  profile: ImportProfile | undefined
  language: string | undefined
  onReload: () => void
}) {
  const { t } = useTranslation()
  const canRun = profile?.can_run ?? false
  const canCommit = profile?.can_commit ?? false
  const canManageMappings = useHasPermission(PERMISSIONS.IMPORTS_MAPPINGS_MANAGE)
  const open = !isTerminal(job.status) && job.status !== 'committing' && job.status !== 'validating'
  const [mappingDirty, setMappingDirty] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const validate = useJobMutation(() => importService.validate(job.public_id, job.version))
  const step = currentStep(job.status, job.mapping_confirmed)
  const validated = VALIDATED.has(job.status)

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <p className="text-sm text-slate-600">
              <Link to="/imports" className="font-medium text-brand-700 hover:underline">
                {t('imp.job.back')}
              </Link>
            </p>
            <h1 className="text-2xl font-bold break-all text-slate-900 sm:text-3xl">{job.original_filename}</h1>
            <p className="text-sm text-slate-600">
              {t('imp.job.facts', {
                profile: job.profile_code,
                version: job.profile_version,
                size: formatBytes(job.file_size, language),
                time: formatDateTime(job.uploaded_at, language),
                by: job.uploaded_by?.display_name ?? '—',
              })}
            </p>
            <p className="font-mono text-xs break-all text-slate-500" title={t('imp.job.hashTitle')}>
              SHA-256 {job.file_sha256}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ImportStatusBadge status={job.status} />
            {canRun && open ? (
              <button type="button" className={secondaryButtonClassName} onClick={() => setCancelling(true)}>
                {t('imp.actions.cancelImport')}
              </button>
            ) : null}
          </div>
        </div>
        <StepIndicator step={step} />
      </header>

      {job.previously_imported_by.length > 0 ? (
        <p role="note" className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <TriangleAlert aria-hidden="true" className="size-5 shrink-0" />
          <span>
            {t('imp.job.sameFile', { count: job.previously_imported_by.length })}{' '}
            {job.previously_imported_by.map((id, index) => (
              <span key={id}>
                {index > 0 ? ', ' : ''}
                <Link to={`/imports/${id}`} className="font-medium underline">
                  {t('imp.job.earlierJob', { index: index + 1 })}
                </Link>
              </span>
            ))}
          </span>
        </p>
      ) : null}

      {!profile ? (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {t('imp.job.profileUnavailable', { code: job.profile_code })}
        </p>
      ) : null}

      {isTerminal(job.status) ? <ResultPanel job={job} language={language} /> : null}

      {profile && (open || job.column_mapping.length > 0) ? (
        <MappingEditor
          job={job}
          profile={profile}
          canEdit={canRun && open}
          onReload={onReload}
          onDirtyChange={setMappingDirty}
        />
      ) : null}

      {canRun && open && job.mapping_confirmed ? (
        <section aria-labelledby="imp-validate" className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 id="imp-validate" className="text-lg font-semibold text-slate-900">
            {t('imp.validate.title')}
          </h2>
          <p className="max-w-3xl text-sm text-slate-600">{t('imp.validate.description')}</p>
          <button
            type="button"
            className={primaryButtonClassName}
            disabled={validate.isPending || mappingDirty}
            onClick={() => validate.mutate()}
          >
            {validate.isPending ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
            {validate.isPending
              ? t('imp.validate.running')
              : validated
                ? t('imp.validate.again')
                : t('imp.validate.run')}
          </button>
          {mappingDirty ? <p className="text-sm text-amber-800">{t('imp.validate.saveFirst')}</p> : null}
          {validate.isError ? <ActionError error={validate.error} onReload={onReload} /> : null}
        </section>
      ) : null}

      {validated && job.validated_at ? (
        <>
          <p className="text-sm text-slate-600">
            {t('imp.validate.validatedAt', {
              time: formatDateTime(job.validated_at, language),
              by: job.validated_by?.display_name ?? '—',
            })}
          </p>
          {job.status === 'validation_failed' ? (
            <InfoNote>
              {t('imp.validate.failedNote')}{' '}
              {canManageMappings ? (
                <Link to="/imports/mappings?status=pending" className="font-medium underline">
                  {t('imp.validate.reviewMappings')}
                </Link>
              ) : null}
            </InfoNote>
          ) : null}
          {job.status === 'ready_for_approval' && profile ? (
            <ApprovalPanel job={job} canCommit={canCommit} onReload={onReload} />
          ) : null}
          <ValidationResults job={job} canDecide={canRun && open} onReload={onReload} />
        </>
      ) : null}

      {cancelling ? <CancelDialog job={job} onClose={() => setCancelling(false)} onReload={onReload} /> : null}
    </div>
  )
}

function ApprovalPanel({ job, canCommit, onReload }: { job: ImportJob; canCommit: boolean; onReload: () => void }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const sectionLabel = useSectionLabel()
  const [reviewed, setReviewed] = useState(false)
  const [applyUpdates, setApplyUpdates] = useState(false)
  const commit = useJobMutation(
    () => importService.commit(job.public_id, { version: job.version, apply_updates: applyUpdates }),
    { refreshEmployees: true },
  )
  const bySection = job.counts.by_section ?? {}
  const updates = Object.values(bySection).reduce((sum, outcomes) => sum + (outcomes.update ?? 0), 0)

  return (
    <section
      aria-labelledby="imp-approve"
      className="space-y-4 rounded-xl border border-brand-200 bg-brand-50/40 p-4 shadow-sm"
    >
      <h2 id="imp-approve" className="text-lg font-semibold text-slate-900">
        {t('imp.approve.title')}
      </h2>
      <p className="max-w-3xl text-sm text-slate-700">{t('imp.approve.description')}</p>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">{t('imp.approve.summaryCaption')}</caption>
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th scope="col" className="px-3 py-2 text-xs font-semibold text-slate-600">
                {t('imp.approve.section')}
              </th>
              {(['new', 'update', 'unchanged', 'skipped'] as const).map((outcome) => (
                <th key={outcome} scope="col" className="px-3 py-2 text-xs font-semibold text-slate-600">
                  {t(`imp.outcomes.${outcome}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Object.entries(bySection).map(([section, outcomes]) => (
              <tr key={section} data-summary={section}>
                <th scope="row" className="px-3 py-2 font-medium text-slate-900">
                  {sectionLabel(section)}
                </th>
                {(['new', 'update', 'unchanged', 'skipped'] as const).map((outcome) => (
                  <td key={outcome} className="px-3 py-2 text-slate-800">
                    {formatCount(outcomes[outcome] ?? 0, language)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {canCommit ? (
        <div className="space-y-3">
          {updates > 0 ? (
            <CheckboxField
              label={t('imp.approve.applyUpdates', { count: updates })}
              hint={
                job.profile_code === 'organisation'
                  ? t('imp.approve.applyUpdatesHintOrganisation')
                  : t('imp.approve.applyUpdatesHint')
              }
              checked={applyUpdates}
              onChange={setApplyUpdates}
            />
          ) : null}
          <CheckboxField label={t('imp.approve.reviewed')} checked={reviewed} onChange={setReviewed} />
          <button
            type="button"
            className={primaryButtonClassName}
            disabled={!reviewed || commit.isPending}
            onClick={() => commit.mutate()}
          >
            {commit.isPending ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
            {commit.isPending ? t('imp.approve.committing') : t('imp.approve.commit')}
          </button>
          <p className="text-sm text-slate-600">{t('imp.approve.recheckNote')}</p>
          {commit.isError ? <ActionError error={commit.error} onReload={onReload} /> : null}
        </div>
      ) : (
        <p className="text-sm text-slate-700">{t('imp.approve.noPermission')}</p>
      )}
    </section>
  )
}

function ResultPanel({ job, language }: { job: ImportJob; language: string | undefined }) {
  const { t } = useTranslation()
  const committed = job.counts.committed
  if (job.status === 'completed' || job.status === 'completed_with_skips') {
    return (
      <section aria-labelledby="imp-result" className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <h2 id="imp-result" className="flex items-center gap-2 text-lg font-semibold text-emerald-900">
          <CircleCheck aria-hidden="true" className="size-5" />
          {t(`imp.result.${job.status}`)}
        </h2>
        <p className="text-sm text-emerald-900">
          {t('imp.result.committedAt', {
            time: job.committed_at ? formatDateTime(job.committed_at, language) : '—',
            by: job.committed_by?.display_name ?? '—',
          })}
        </p>
        {committed ? (
          <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <CountTile label={t('imp.result.created')} value={formatCount(committed.created, language)} tone="emerald" />
            <CountTile label={t('imp.result.updated')} value={formatCount(committed.updated, language)} tone="brand" />
            <CountTile label={t('imp.result.unchanged')} value={formatCount(committed.unchanged, language)} />
            <CountTile label={t('imp.result.skipped')} value={formatCount(committed.skipped, language)} tone="amber" />
          </dl>
        ) : null}
      </section>
    )
  }
  const closed = job.status === 'failed' || job.status === 'expired' ? job.status : 'cancelled'
  const tone = closed === 'failed' ? 'border-red-200 bg-red-50 text-red-900' : 'border-slate-200 bg-slate-50 text-slate-800'
  return (
    <section aria-labelledby="imp-result" className={`space-y-2 rounded-xl border p-4 ${tone}`}>
      <h2 id="imp-result" className="text-lg font-semibold">
        {t(`imp.result.${closed}`)}
      </h2>
      <p className="text-sm">{t(`imp.result.${closed}Body`)}</p>
    </section>
  )
}

function CancelDialog({ job, onClose, onReload }: { job: ImportJob; onClose: () => void; onReload: () => void }) {
  const { t } = useTranslation()
  const cancel = useJobMutation(() => importService.cancel(job.public_id, job.version))
  return (
    <Modal title={t('imp.cancelDialog.title')} description={t('imp.cancelDialog.description')} onClose={onClose} busy={cancel.isPending}>
      <div className="space-y-4">
        {cancel.isError ? (
          <ActionError
            error={cancel.error}
            onReload={() => {
              onReload()
              onClose()
            }}
          />
        ) : null}
        <div className="flex flex-wrap justify-end gap-3">
          <button type="button" className={secondaryButtonClassName} onClick={onClose} disabled={cancel.isPending}>
            {t('imp.actions.keepImport')}
          </button>
          <button
            type="button"
            className={primaryButtonClassName}
            disabled={cancel.isPending}
            onClick={() => cancel.mutate(undefined, { onSuccess: onClose })}
          >
            {t('imp.actions.cancelImport')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
