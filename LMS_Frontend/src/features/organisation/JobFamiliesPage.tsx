import { PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService } from '../../services/organisationService'
import type { JobFamily } from '../../types/organisation'
import { AdminErrorState, Cell, HeaderCell } from '../admin/AdminParts'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { ListToolbar } from './ListParts'
import { textMatches } from './names'
import {
  ActiveBadge,
  ChangeError,
  CheckboxField,
  DialogActions,
  NoticeBanner,
  OrgPageHeader,
  RowButton,
  SelectField,
  TextAreaField,
  TextField,
  type SuccessNotice,
} from './OrgParts'
import { useJobFamilies, useOrgMutation, useReloadAndClose } from './orgQueries'

/** Families below `id` in the loaded list (a family cannot sit under its own descendant). */
function familyDescendants(families: readonly JobFamily[], id: string): Set<string> {
  const result = new Set<string>()
  let added = true
  while (added) {
    added = false
    for (const family of families) {
      const parent = family.parent?.public_id
      if (parent && (parent === id || result.has(parent)) && !result.has(family.public_id)) {
        result.add(family.public_id)
        added = true
      }
    }
  }
  return result
}

/** Job families (`/organisation/job-families`), optionally nested. */
export function JobFamiliesPage() {
  const { t } = useTranslation()
  const canManage = useHasPermission(PERMISSIONS.DESIGNATIONS_MANAGE)
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editing, setEditing] = useState<JobFamily | 'new' | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useJobFamilies(includeInactive)
  useRefreshSessionOnForbidden(query.error)
  const all = query.data ?? []
  const families = all.filter((family) =>
    textMatches([family.code, family.name, family.description, family.parent?.name], search),
  )
  const columns = {
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    parent: t('org.jobFamilies.parent'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.jobFamilies.title')}
        subtitle={t('org.jobFamilies.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.jobFamilies.create')}
          </button>
        }
      />
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t('org.jobFamilies.title')}
        search={search}
        onSearch={setSearch}
        placeholder={t('org.common.searchCodeOrName')}
        includeInactive={includeInactive}
        onIncludeInactive={setIncludeInactive}
      />
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <AdminErrorState
          title={t('org.jobFamilies.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('org.jobFamilies.title')}</caption>
            <thead className={TABLE_LAYOUTS.md.head}>
              <tr>
                {Object.entries(columns)
                  .filter(([key]) => canManage || key !== 'actions')
                  .map(([key, label]) => (
                    <HeaderCell key={key}>{label}</HeaderCell>
                  ))}
              </tr>
            </thead>
            <tbody className={TABLE_LAYOUTS.md.body}>
              {families.map((family) => (
                <tr key={family.public_id} className={TABLE_LAYOUTS.md.row}>
                  <Cell label={columns.name}>
                    <span className="font-medium text-slate-900">{family.name}</span>
                    {family.description ? <span className="block text-xs text-slate-600">{family.description}</span> : null}
                  </Cell>
                  <Cell label={columns.code}>
                    <span className="font-mono">{family.code}</span>
                  </Cell>
                  <Cell label={columns.parent}>{family.parent ? family.parent.name : '—'}</Cell>
                  <Cell label={columns.status}>
                    <ActiveBadge active={family.is_active} />
                  </Cell>
                  {canManage ? (
                    <Cell label={columns.actions}>
                      <RowButton onClick={() => setEditing(family)} label={t('org.actions.editNamed', { name: family.name })}>
                        <PencilLine aria-hidden="true" className="size-4" />
                        {t('org.actions.edit')}
                      </RowButton>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {families.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.jobFamilies.empty')}</p> : null}
        </div>
      )}
      {editing !== null ? (
        <JobFamilyDialog
          family={editing === 'new' ? undefined : editing}
          families={all}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            setNotice({ message, warnings: [] })
          }}
        />
      ) : null}
    </div>
  )
}

function JobFamilyDialog({
  family,
  families,
  onClose,
  onDone,
}: {
  family?: JobFamily
  families: readonly JobFamily[]
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const [code, setCode] = useState(family?.code ?? '')
  const [name, setName] = useState(family?.name ?? '')
  const [description, setDescription] = useState(family?.description ?? '')
  const [parentId, setParentId] = useState(family?.parent?.public_id ?? '')
  const [active, setActive] = useState(family?.is_active ?? true)
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    family
      ? organisationService.updateJobFamily(family.public_id, { ...body, version: family.version })
      : organisationService.createJobFamily(body),
  )

  const excluded = family ? familyDescendants(families, family.public_id).add(family.public_id) : new Set<string>()
  const parentOptions = families
    .filter((candidate) => !excluded.has(candidate.public_id) && candidate.is_active)
    .map((candidate) => ({ value: candidate.public_id, label: `${candidate.name} (${candidate.code})` }))
  const errors = {
    code: code.trim() === '' ? t('org.errors.required') : undefined,
    name: name.trim() === '' ? t('org.errors.required') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name) return
    const values = {
      code: code.trim(),
      name: name.trim(),
      description: description.trim() === '' ? null : description.trim(),
      parent_id: parentId || null,
    }
    let body: Record<string, unknown> = values
    if (family) {
      body = {}
      if (values.code !== family.code) body.code = values.code
      if (values.name !== family.name) body.name = values.name
      if (values.description !== family.description) body.description = values.description
      if (values.parent_id !== (family.parent?.public_id ?? null)) body.parent_id = values.parent_id
      if (active !== family.is_active) body.is_active = active
      if (Object.keys(body).length === 0) {
        onClose()
        return
      }
    }
    mutation.mutate(body, {
      onSuccess: (result) => onDone(t(family ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={family ? t('org.jobFamilies.editTitle', { name: family.name }) : t('org.jobFamilies.createTitle')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <TextField
          label={t('org.fields.code')}
          value={code}
          onChange={setCode}
          required
          maxLength={50}
          hint={t('org.hints.code')}
          error={showErrors ? errors.code : undefined}
          autoFocus
        />
        <TextField
          label={t('org.fields.name')}
          value={name}
          onChange={setName}
          required
          maxLength={200}
          error={showErrors ? errors.name : undefined}
        />
        <SelectField
          label={t('org.jobFamilies.parent')}
          value={parentId}
          onChange={setParentId}
          options={parentOptions}
          emptyLabel={t('org.common.none')}
          hint={t('org.jobFamilies.parentHint')}
        />
        <TextAreaField label={t('org.fields.description')} value={description} onChange={setDescription} maxLength={500} />
        {family ? (
          <CheckboxField label={t('org.fields.activeLabel')} checked={active} onChange={setActive} hint={t('org.hints.inactive')} />
        ) : null}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={family ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}
