import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'

import { primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { formatDateTime, todayIsoDate } from '../../lib/format'
import { importService } from '../../services/importService'
import {
  isMappingKind,
  isMappingStatus,
  MAPPING_KINDS,
  MAPPING_STATUSES,
  type MappingKind,
  type ValueMapping,
} from '../../types/imports'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { DesignationSelect, LocationSelect, RankedSelect, UnitSelect } from '../employees/EmployeeFormParts'
import { ListFooter } from '../organisation/ListParts'
import { InfoNote, SelectField, TextAreaField } from '../organisation/OrgParts'
import { ActionError, ImportErrorState, MappingStatusBadge } from './ImportParts'
import { useMappingMutation, useValueMappings } from './importQueries'

type Dialog = { mapping: ValueMapping; action: 'approve' | 'reject' | 'withdraw' }

/**
 * Reference mapping review queue (`imports.view`; decisions need
 * `imports.mappings.manage`). Unfamiliar labels from workbooks (designations,
 * units, locations, grades, levels) wait here with ranked suggestions. Nothing is
 * mapped until a person approves a target; the original text is kept, and a
 * decision can be withdrawn later (it stays in the history).
 */
export function MappingsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [params, setParams] = useSearchParams()
  const kindParam = params.get('kind')
  const statusParam = params.get('status')
  const kind = isMappingKind(kindParam) ? kindParam : undefined
  const status = statusParam === 'all' ? undefined : isMappingStatus(statusParam) ? statusParam : 'pending'
  const canManage = useHasPermission(PERMISSIONS.IMPORTS_MAPPINGS_MANAGE)
  const mappings = useValueMappings({ kind, status })
  useRefreshSessionOnForbidden(mappings.error)
  const [dialog, setDialog] = useState<Dialog | null>(null)
  const items = mappings.data?.pages.flatMap((page) => page.items) ?? []

  function update(key: 'kind' | 'status', value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  return (
    <div className="space-y-6">
      <header className="min-w-0 space-y-1">
        <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{t('imp.mappings.title')}</h1>
        <p className="max-w-3xl text-slate-600">{t('imp.mappings.subtitle')}</p>
      </header>
      <InfoNote>{t('imp.mappings.neverAutomatic')}</InfoNote>

      <div className="grid gap-3 sm:grid-cols-2 lg:w-2/3">
        <SelectField
          label={t('imp.mappings.kindFilter')}
          value={kind ?? ''}
          onChange={(value) => update('kind', value)}
          emptyLabel={t('imp.mappings.allKinds')}
          options={MAPPING_KINDS.map((value) => ({ value, label: t(`imp.kinds.${value}`) }))}
        />
        <SelectField
          label={t('imp.mappings.statusFilter')}
          value={statusParam === 'all' ? 'all' : (status ?? '')}
          onChange={(value) => update('status', value)}
          options={[
            ...MAPPING_STATUSES.map((value) => ({ value, label: t(`imp.mappingStatus.${value}`) })),
            { value: 'all', label: t('imp.mappings.allStatuses') },
          ]}
        />
      </div>

      {mappings.isPending ? (
        <LoadingState />
      ) : mappings.isError && items.length === 0 ? (
        <ImportErrorState
          title={t('imp.mappings.loadError')}
          error={mappings.error}
          onRetry={() => void mappings.refetch()}
          isRetrying={mappings.isFetching}
        />
      ) : (
        <>
          <ul className="space-y-3">
            {items.map((mapping) => (
              <li
                key={mapping.public_id}
                className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                data-mapping={mapping.source_text}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <MappingStatusBadge status={mapping.status} />
                  <span className="text-sm text-slate-600">
                    {isMappingKind(mapping.kind) ? t(`imp.kinds.${mapping.kind}`) : mapping.kind}
                  </span>
                </div>
                <p className="text-base font-semibold break-words text-slate-900">
                  {t('imp.mappings.sourceText', { text: mapping.source_text })}
                </p>
                {mapping.target ? (
                  <p className="text-sm break-words text-slate-800">
                    {t('imp.mappings.mappedTo', { name: mapping.target.name, code: mapping.target.code })}
                  </p>
                ) : null}
                {mapping.decided_at ? (
                  <p className="text-sm text-slate-600">
                    {t('imp.mappings.decided', {
                      time: formatDateTime(mapping.decided_at, language),
                      by: mapping.decided_by?.display_name ?? '—',
                    })}
                    {mapping.decision_reason ? ` · ${mapping.decision_reason}` : ''}
                  </p>
                ) : null}
                {mapping.status === 'pending' && mapping.suggestions.length > 0 ? (
                  <div className="text-sm">
                    <p className="font-medium text-slate-800">{t('imp.mappings.suggestions')}</p>
                    <ul className="list-disc pl-5 text-slate-700">
                      {mapping.suggestions.map((suggestion) => (
                        <li key={suggestion.public_id}>
                          {suggestion.label} ({suggestion.code})
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {canManage ? (
                  <div className="flex flex-wrap gap-2">
                    {mapping.status === 'pending' ? (
                      <>
                        <button
                          type="button"
                          className={primaryButtonClassName}
                          onClick={() => setDialog({ mapping, action: 'approve' })}
                        >
                          {t('imp.mappings.approve')}
                        </button>
                        <button
                          type="button"
                          className={secondaryButtonClassName}
                          onClick={() => setDialog({ mapping, action: 'reject' })}
                        >
                          {t('imp.mappings.reject')}
                        </button>
                      </>
                    ) : mapping.status === 'approved' || mapping.status === 'rejected' ? (
                      <button
                        type="button"
                        className={secondaryButtonClassName}
                        onClick={() => setDialog({ mapping, action: 'withdraw' })}
                      >
                        {t('imp.mappings.withdraw')}
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
          {items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
              {t('imp.mappings.empty')}
            </p>
          ) : null}
          <ListFooter
            countText={t('imp.mappings.count', { count: items.length })}
            hasMore={Boolean(mappings.hasNextPage)}
            loadingMore={mappings.isFetchingNextPage}
            onLoadMore={() => void mappings.fetchNextPage()}
          />
        </>
      )}
      {dialog ? <DecisionDialog {...dialog} onClose={() => setDialog(null)} /> : null}
    </div>
  )
}

function DecisionDialog({ mapping, action, onClose }: Dialog & { onClose: () => void }) {
  const { t } = useTranslation()
  const [target, setTarget] = useState(mapping.suggestions.length === 1 ? mapping.suggestions[0].public_id : '')
  const [other, setOther] = useState('')
  const [reason, setReason] = useState('')
  const [touched, setTouched] = useState(false)
  const chosen = target === 'other' ? other : target
  const mutation = useMappingMutation(() => {
    const body = { version: mapping.version, reason: reason.trim() || null }
    if (action === 'approve') return importService.approveMapping(mapping.public_id, { ...body, target_public_id: chosen })
    if (action === 'reject') return importService.rejectMapping(mapping.public_id, body)
    return importService.withdrawMapping(mapping.public_id, body)
  })
  const missingTarget = action === 'approve' && !chosen

  function submit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (missingTarget) return
    mutation.mutate(undefined, { onSuccess: onClose })
  }

  return (
    <Modal
      title={t(`imp.mappingDialog.${action}.title`)}
      description={t(`imp.mappingDialog.${action}.description`, { text: mapping.source_text })}
      onClose={onClose}
      busy={mutation.isPending}
      size={action === 'approve' ? 'lg' : 'md'}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {action === 'approve' ? (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-800">{t('imp.mappingDialog.approve.target')}</legend>
            {mapping.suggestions.map((suggestion) => (
              <label key={suggestion.public_id} className="flex items-start gap-2 text-sm text-slate-800">
                <input
                  type="radio"
                  name="target"
                  value={suggestion.public_id}
                  checked={target === suggestion.public_id}
                  onChange={() => setTarget(suggestion.public_id)}
                  className="mt-0.5 size-4 accent-brand-700"
                />
                <span className="break-words">
                  {suggestion.label} ({suggestion.code})
                </span>
              </label>
            ))}
            <label className="flex items-start gap-2 text-sm text-slate-800">
              <input
                type="radio"
                name="target"
                value="other"
                checked={target === 'other'}
                onChange={() => setTarget('other')}
                className="mt-0.5 size-4 accent-brand-700"
              />
              {t('imp.mappingDialog.approve.other')}
            </label>
            {target === 'other' && isMappingKind(mapping.kind) ? (
              <TargetPicker kind={mapping.kind} value={other} onChange={setOther} />
            ) : null}
            {touched && missingTarget ? (
              <p role="alert" className="text-sm text-red-700">
                {t('imp.mappingDialog.approve.targetMissing')}
              </p>
            ) : null}
          </fieldset>
        ) : null}
        <TextAreaField label={t('imp.mappingDialog.reason')} value={reason} onChange={setReason} maxLength={500} />
        {action !== 'reject' ? <p className="text-sm text-slate-600">{t('imp.mappingDialog.revalidateNote')}</p> : null}
        {mutation.isError ? <ActionError error={mutation.error} /> : null}
        <div className="flex flex-wrap justify-end gap-3">
          <button type="button" className={secondaryButtonClassName} onClick={onClose} disabled={mutation.isPending}>
            {t('imp.actions.cancel')}
          </button>
          <button type="submit" className={primaryButtonClassName} disabled={mutation.isPending}>
            {t(`imp.mappingDialog.${action}.confirm`)}
          </button>
        </div>
      </form>
    </Modal>
  )
}

/** Any active record of the mapping's kind (the same pickers as the employee forms). */
function TargetPicker({
  kind,
  value,
  onChange,
}: {
  kind: MappingKind
  value: string
  onChange: (value: string) => void
}) {
  const { t } = useTranslation()
  switch (kind) {
    case 'org_unit':
      return (
        <UnitSelect label={t('imp.kinds.org_unit')} value={value} onChange={onChange} asOf={todayIsoDate()} required />
      )
    case 'designation':
      return <DesignationSelect value={value} onChange={onChange} />
    case 'location':
      return <LocationSelect value={value} onChange={onChange} />
    case 'grade':
      return <RankedSelect kind="grades" value={value} onChange={onChange} />
    case 'job_level':
      return <RankedSelect kind="levels" value={value} onChange={onChange} />
  }
}
