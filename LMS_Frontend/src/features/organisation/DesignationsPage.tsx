import { Link2, PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { formatDate } from '../../lib/format'
import { organisationService, translationChanges } from '../../services/organisationService'
import type { Designation, DesignationRoleMapping, ListFilters } from '../../types/organisation'
import { AdminErrorState, Cell, HeaderCell } from '../admin/AdminParts'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { ListFooter, ListToolbar } from './ListParts'
import { localName, localTitle } from './names'
import {
  ActiveBadge,
  ChangeError,
  CheckboxField,
  DialogActions,
  InfoNote,
  NoticeBanner,
  OrgPageHeader,
  RowButton,
  SelectField,
  TextAreaField,
  TextField,
  TranslationFields,
  type SuccessNotice,
} from './OrgParts'
import {
  useDesignations,
  useJobFamilies,
  useMappings,
  useOrgMutation,
  useOrgTree,
  useReloadAndClose,
  useRolePicker,
} from './orgQueries'

/** Designations (`/organisation/designations`) and their functional-role mappings. */
export function DesignationsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManage = useHasPermission(PERMISSIONS.DESIGNATIONS_MANAGE)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<ListFilters>({})
  const [editing, setEditing] = useState<Designation | 'new' | null>(null)
  const [mapping, setMapping] = useState<Designation | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useDesignations(filters)
  useRefreshSessionOnForbidden(query.error)
  const items = query.data?.pages.flatMap((page) => page.items) ?? []
  const columns = {
    title: t('org.fields.title'),
    code: t('org.fields.code'),
    family: t('org.fields.jobFamily'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.designations.title')}
        subtitle={t('org.designations.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.designations.create')}
          </button>
        }
      />
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t('org.designations.title')}
        search={search}
        onSearch={setSearch}
        placeholder={t('org.common.searchCodeOrName')}
        includeInactive={Boolean(filters.include_inactive)}
        onIncludeInactive={(value) => setFilters((current) => ({ ...current, include_inactive: value || undefined }))}
        onSubmit={() => setFilters((current) => ({ ...current, q: search.trim() || undefined }))}
      />
      {query.isPending ? (
        <LoadingState />
      ) : query.isError && items.length === 0 ? (
        <AdminErrorState
          title={t('org.designations.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('org.designations.title')}</caption>
              <thead className={TABLE_LAYOUTS.md.head}>
                <tr>
                  {Object.entries(columns).map(([key, label]) => (
                    <HeaderCell key={key}>{label}</HeaderCell>
                  ))}
                </tr>
              </thead>
              <tbody className={TABLE_LAYOUTS.md.body}>
                {items.map((designation) => {
                  const title = localTitle(designation, language)
                  return (
                    <tr key={designation.public_id} className={TABLE_LAYOUTS.md.row}>
                      <Cell label={columns.title}>
                        <span className="font-medium text-slate-900">{title}</span>
                      </Cell>
                      <Cell label={columns.code}>
                        <span className="font-mono">{designation.code}</span>
                      </Cell>
                      <Cell label={columns.family}>{designation.job_family?.name ?? '—'}</Cell>
                      <Cell label={columns.status}>
                        <ActiveBadge active={designation.is_active} />
                      </Cell>
                      <Cell label={columns.actions}>
                        <span className="flex flex-wrap gap-2">
                          <RowButton
                            onClick={() => setMapping(designation)}
                            label={t('org.designations.rolesNamed', { name: title })}
                          >
                            <Link2 aria-hidden="true" className="size-4" />
                            {t('org.designations.roles')}
                          </RowButton>
                          {canManage ? (
                            <RowButton onClick={() => setEditing(designation)} label={t('org.actions.editNamed', { name: title })}>
                              <PencilLine aria-hidden="true" className="size-4" />
                              {t('org.actions.edit')}
                            </RowButton>
                          ) : null}
                        </span>
                      </Cell>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {items.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.designations.empty')}</p> : null}
          </div>
          <ListFooter
            countText={t('org.common.count', { count: items.length })}
            hasMore={query.hasNextPage}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
          />
        </div>
      )}
      {editing !== null ? (
        <DesignationDialog
          designation={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            setNotice({ message, warnings: [] })
          }}
        />
      ) : null}
      {mapping !== null ? <MappingsDialog designation={mapping} onClose={() => setMapping(null)} /> : null}
    </div>
  )
}

function DesignationDialog({
  designation,
  onClose,
  onDone,
}: {
  designation?: Designation
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const families = useJobFamilies(false)
  const [code, setCode] = useState(designation?.code ?? '')
  const [title, setTitle] = useState(designation?.title ?? '')
  const [familyId, setFamilyId] = useState(designation?.job_family?.public_id ?? '')
  const [active, setActive] = useState(designation?.is_active ?? true)
  const [translations, setTranslations] = useState<Record<string, string>>({ ...(designation?.translations ?? {}) })
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    designation
      ? organisationService.updateDesignation(designation.public_id, { ...body, version: designation.version })
      : organisationService.createDesignation(body),
  )
  const familyOptions = (families.data ?? []).map((family) => ({
    value: family.public_id,
    label: `${family.name} (${family.code})`,
  }))
  if (designation?.job_family && !familyOptions.some((option) => option.value === designation.job_family?.public_id)) {
    familyOptions.push({ value: designation.job_family.public_id, label: designation.job_family.name })
  }
  const errors = {
    code: code.trim() === '' ? t('org.errors.required') : undefined,
    title: title.trim() === '' ? t('org.errors.required') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.title) return
    let body: Record<string, unknown>
    if (designation) {
      body = {}
      if (code.trim() !== designation.code) body.code = code.trim()
      if (title.trim() !== designation.title) body.title = title.trim()
      if ((familyId || null) !== (designation.job_family?.public_id ?? null)) body.job_family_id = familyId || null
      if (active !== designation.is_active) body.is_active = active
      const changes = translationChanges(designation.translations, translations)
      if (changes) body.translations = changes
      if (Object.keys(body).length === 0) {
        onClose()
        return
      }
    } else {
      body = {
        code: code.trim(),
        title: title.trim(),
        job_family_id: familyId || null,
        translations: translationChanges({}, translations) ?? {},
      }
    }
    mutation.mutate(body, {
      onSuccess: (result) =>
        onDone(t(designation ? 'org.messages.saved' : 'org.messages.created', { name: result.title })),
    })
  }

  return (
    <Modal
      title={designation ? t('org.designations.editTitle', { name: designation.title }) : t('org.designations.createTitle')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
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
            label={t('org.fields.title')}
            value={title}
            onChange={setTitle}
            required
            maxLength={200}
            error={showErrors ? errors.title : undefined}
          />
          <SelectField
            label={t('org.fields.jobFamily')}
            value={familyId}
            onChange={setFamilyId}
            options={familyOptions}
            emptyLabel={t('org.common.none')}
          />
        </div>
        {designation ? (
          <CheckboxField
            label={t('org.fields.activeLabel')}
            checked={active}
            onChange={setActive}
            hint={t('org.designations.inactiveHint')}
          />
        ) : null}
        <TranslationFields values={translations} onChange={setTranslations} />
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={designation ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}

/** Functional roles implied by a designation (many-to-many, dated, optionally unit-scoped). */
function MappingsDialog({ designation, onClose }: { designation: Designation; onClose: () => void }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManageRoles = useHasPermission(PERMISSIONS.FUNCTIONAL_ROLES_MANAGE)
  const [includeEnded, setIncludeEnded] = useState(false)
  const [ending, setEnding] = useState<DesignationRoleMapping | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useMappings(designation.public_id, includeEnded)
  const title = localTitle(designation, language)

  return (
    <Modal title={t('org.designations.mappingsTitle', { name: title })} onClose={onClose} size="lg">
      <div className="space-y-4">
        <InfoNote>{t('org.functionalRoles.notAccessRoles')}</InfoNote>
        {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
        <CheckboxField label={t('org.designations.showEnded')} checked={includeEnded} onChange={setIncludeEnded} />
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <AdminErrorState
            title={t('org.designations.mappingsLoadError')}
            error={query.error}
            onRetry={() => void query.refetch()}
            isRetrying={query.isFetching}
          />
        ) : query.data.length === 0 ? (
          <p className="text-sm text-slate-600">{t('org.designations.noMappings')}</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
            {query.data.map((item) => (
              <li key={item.public_id} className="flex flex-wrap items-start justify-between gap-2 px-3 py-2 text-sm">
                <div className="min-w-0 space-y-0.5">
                  <p className="font-medium break-words text-slate-900">
                    {item.functional_role.name}{' '}
                    <span className="font-mono text-xs text-slate-500">{item.functional_role.code}</span>
                  </p>
                  <p className="break-words text-slate-700">
                    {item.scope_unit
                      ? t(item.include_descendants ? 'org.designations.scopeWithSubUnits' : 'org.designations.scopeOnly', {
                          name: item.scope_unit.name,
                        })
                      : t('org.designations.scopeEverywhere')}
                  </p>
                  <p className="text-xs text-slate-600">
                    {t('org.designations.period', {
                      from: item.effective_from ? formatDate(item.effective_from, language) : t('org.common.notRecorded'),
                      to: item.effective_to ? formatDate(item.effective_to, language) : t('org.common.open'),
                    })}
                  </p>
                </div>
                {canManageRoles && item.effective_to === null ? (
                  <RowButton
                    onClick={() => setEnding(item)}
                    label={t('org.designations.endNamed', { name: item.functional_role.name })}
                  >
                    {t('org.designations.end')}
                  </RowButton>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {ending ? (
          <EndMappingForm
            designationId={designation.public_id}
            mapping={ending}
            onCancel={() => setEnding(null)}
            onDone={(message) => {
              setEnding(null)
              setNotice({ message, warnings: [] })
            }}
          />
        ) : canManageRoles ? (
          <AddMappingForm
            designationId={designation.public_id}
            onDone={(message) => setNotice({ message, warnings: [] })}
          />
        ) : (
          <p className="text-sm text-slate-600">{t('org.designations.readOnlyMappings')}</p>
        )}
      </div>
    </Modal>
  )
}

function AddMappingForm({ designationId, onDone }: { designationId: string; onDone: (message: string) => void }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const roles = useRolePicker(true)
  const tree = useOrgTree({})
  const [roleId, setRoleId] = useState('')
  const [scopeId, setScopeId] = useState('')
  const [descendants, setDescendants] = useState(true)
  const [from, setFrom] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const mutation = useOrgMutation(
    (body: { functional_role_id: string; scope_unit_id: string | null; include_descendants: boolean; effective_from: string | null }) =>
      organisationService.createMapping(designationId, body),
  )
  const roleError = roleId === '' ? t('org.errors.required') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (roleError) return
    mutation.mutate(
      { functional_role_id: roleId, scope_unit_id: scopeId || null, include_descendants: descendants, effective_from: from || null },
      {
        onSuccess: (result) => {
          setRoleId('')
          setScopeId('')
          setFrom('')
          setShowErrors(false)
          onDone(t('org.designations.mappingAdded', { name: result.functional_role.name }))
        },
      },
    )
  }

  const roleOptions = (roles.data?.items ?? []).map((role) => ({
    value: role.public_id,
    label: `${localName(role, language)} (${role.code})`,
  }))
  const unitOptions = (tree.data?.nodes ?? [])
    .map((node) => ({ value: node.public_id, label: `${localName(node, language)} (${node.code})` }))
    .sort((a, b) => a.label.localeCompare(b.label))

  return (
    <form noValidate onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 p-3">
      <h3 className="text-sm font-semibold text-slate-900">{t('org.designations.addMapping')}</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label={t('org.fields.functionalRole')}
          value={roleId}
          onChange={setRoleId}
          options={roleOptions}
          emptyLabel={t('org.common.choose')}
          required
          error={showErrors ? roleError : undefined}
        />
        <SelectField
          label={t('org.fields.scope')}
          value={scopeId}
          onChange={setScopeId}
          options={unitOptions}
          emptyLabel={t('org.designations.scopeEverywhere')}
          hint={t('org.designations.scopeHint')}
        />
        <TextField
          label={t('org.fields.effectiveFrom')}
          type="date"
          value={from}
          onChange={setFrom}
          hint={t('org.designations.fromHint')}
        />
      </div>
      {scopeId ? (
        <CheckboxField label={t('org.designations.includeSubUnits')} checked={descendants} onChange={setDescendants} />
      ) : null}
      {mutation.isError ? <ChangeError error={mutation.error} /> : null}
      <div className="flex justify-end">
        <button type="submit" disabled={mutation.isPending} className={primaryButtonClassName}>
          {mutation.isPending ? t('org.actions.saving') : t('org.designations.addMapping')}
        </button>
      </div>
    </form>
  )
}

function EndMappingForm({
  designationId,
  mapping,
  onCancel,
  onDone,
}: {
  designationId: string
  mapping: DesignationRoleMapping
  onCancel: () => void
  onDone: (message: string) => void
}) {
  const { t, i18n } = useTranslation()
  const [to, setTo] = useState('')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const mutation = useOrgMutation((body: { effective_to: string; reason: string | null }) =>
    organisationService.endMapping(designationId, mapping.public_id, body),
  )
  const dateError = to === '' ? t('org.errors.required') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (dateError) return
    mutation.mutate(
      { effective_to: to, reason: reason.trim() || null },
      {
        onSuccess: () =>
          onDone(
            t('org.designations.mappingEnded', {
              name: mapping.functional_role.name,
              date: formatDate(to, i18n.resolvedLanguage),
            }),
          ),
      },
    )
  }

  return (
    <form noValidate onSubmit={submit} className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <h3 className="text-sm font-semibold text-amber-950">
        {t('org.designations.endTitle', { name: mapping.functional_role.name })}
      </h3>
      <TextField
        label={t('org.designations.endDate')}
        type="date"
        value={to}
        onChange={setTo}
        required
        hint={t('org.designations.endHint')}
        error={showErrors ? dateError : undefined}
        autoFocus
      />
      <TextAreaField label={t('org.fields.reason')} value={reason} onChange={setReason} maxLength={500} />
      {mutation.isError ? <ChangeError error={mutation.error} /> : null}
      <DialogActions onCancel={onCancel} busy={mutation.isPending} submitLabel={t('org.designations.confirmEnd')} />
    </form>
  )
}
