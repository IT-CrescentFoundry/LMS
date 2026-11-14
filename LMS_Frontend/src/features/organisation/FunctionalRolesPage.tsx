import { PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService, translationChanges } from '../../services/organisationService'
import type { FunctionalRole, ListFilters } from '../../types/organisation'
import { AdminErrorState, Cell, HeaderCell } from '../admin/AdminParts'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { ListFooter, ListToolbar } from './ListParts'
import { localName } from './names'
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
  useFunctionalRoles,
  useJobFamilies,
  useOrgMutation,
  useOrgTree,
  useReloadAndClose,
} from './orgQueries'

/**
 * Functional roles (`/organisation/functional-roles`): the work people do.
 * They are not LMS access roles and grant no permissions.
 */
export function FunctionalRolesPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManage = useHasPermission(PERMISSIONS.FUNCTIONAL_ROLES_MANAGE)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<ListFilters>({})
  const [editing, setEditing] = useState<FunctionalRole | 'new' | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useFunctionalRoles(filters)
  useRefreshSessionOnForbidden(query.error)
  const items = query.data?.pages.flatMap((page) => page.items) ?? []
  const columns = {
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    family: t('org.fields.jobFamily'),
    owner: t('org.fields.ownerUnit'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.functionalRoles.title')}
        subtitle={t('org.functionalRoles.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.functionalRoles.create')}
          </button>
        }
      />
      <InfoNote>
        {t('org.functionalRoles.notAccessRoles')}{' '}
        <Link to="/organisation/designations" className="font-medium underline focus:ring-2 focus:ring-brand-500 focus:outline-none">
          {t('org.functionalRoles.mappingsLink')}
        </Link>
      </InfoNote>
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t('org.functionalRoles.title')}
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
          title={t('org.functionalRoles.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('org.functionalRoles.title')}</caption>
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
                {items.map((role) => {
                  const name = localName(role, language)
                  return (
                    <tr key={role.public_id} className={TABLE_LAYOUTS.md.row}>
                      <Cell label={columns.name}>
                        <span className="font-medium text-slate-900">{name}</span>
                        {role.description ? <span className="block text-xs text-slate-600">{role.description}</span> : null}
                      </Cell>
                      <Cell label={columns.code}>
                        <span className="font-mono">{role.code}</span>
                      </Cell>
                      <Cell label={columns.family}>{role.job_family?.name ?? '—'}</Cell>
                      <Cell label={columns.owner}>{role.owner_unit?.name ?? '—'}</Cell>
                      <Cell label={columns.status}>
                        <ActiveBadge active={role.is_active} />
                      </Cell>
                      {canManage ? (
                        <Cell label={columns.actions}>
                          <RowButton onClick={() => setEditing(role)} label={t('org.actions.editNamed', { name })}>
                            <PencilLine aria-hidden="true" className="size-4" />
                            {t('org.actions.edit')}
                          </RowButton>
                        </Cell>
                      ) : null}
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {items.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.functionalRoles.empty')}</p> : null}
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
        <FunctionalRoleDialog
          role={editing === 'new' ? undefined : editing}
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

function FunctionalRoleDialog({
  role,
  onClose,
  onDone,
}: {
  role?: FunctionalRole
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const families = useJobFamilies(false)
  const tree = useOrgTree({})
  const [code, setCode] = useState(role?.code ?? '')
  const [name, setName] = useState(role?.name ?? '')
  const [description, setDescription] = useState(role?.description ?? '')
  const [familyId, setFamilyId] = useState(role?.job_family?.public_id ?? '')
  const [ownerId, setOwnerId] = useState(role?.owner_unit?.public_id ?? '')
  const [active, setActive] = useState(role?.is_active ?? true)
  const [translations, setTranslations] = useState<Record<string, string>>({ ...(role?.translations ?? {}) })
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    role
      ? organisationService.updateFunctionalRole(role.public_id, { ...body, version: role.version })
      : organisationService.createFunctionalRole(body),
  )

  const familyOptions = (families.data ?? []).map((family) => ({ value: family.public_id, label: `${family.name} (${family.code})` }))
  if (role?.job_family && !familyOptions.some((option) => option.value === role.job_family?.public_id)) {
    familyOptions.push({ value: role.job_family.public_id, label: role.job_family.name })
  }
  const unitOptions = (tree.data?.nodes ?? [])
    .map((node) => ({ value: node.public_id, label: `${localName(node, language)} (${node.code})` }))
    .sort((a, b) => a.label.localeCompare(b.label))
  if (role?.owner_unit && !unitOptions.some((option) => option.value === role.owner_unit?.public_id)) {
    unitOptions.push({ value: role.owner_unit.public_id, label: role.owner_unit.name })
  }
  const errors = {
    code: code.trim() === '' ? t('org.errors.required') : undefined,
    name: name.trim() === '' ? t('org.errors.required') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name) return
    const descriptionValue = description.trim() === '' ? null : description.trim()
    let body: Record<string, unknown>
    if (role) {
      body = {}
      if (code.trim() !== role.code) body.code = code.trim()
      if (name.trim() !== role.name) body.name = name.trim()
      if (descriptionValue !== role.description) body.description = descriptionValue
      if ((familyId || null) !== (role.job_family?.public_id ?? null)) body.job_family_id = familyId || null
      if ((ownerId || null) !== (role.owner_unit?.public_id ?? null)) body.owner_unit_id = ownerId || null
      if (active !== role.is_active) body.is_active = active
      const changes = translationChanges(role.translations, translations)
      if (changes) body.translations = changes
      if (Object.keys(body).length === 0) {
        onClose()
        return
      }
    } else {
      body = {
        code: code.trim(),
        name: name.trim(),
        description: descriptionValue,
        job_family_id: familyId || null,
        owner_unit_id: ownerId || null,
        translations: translationChanges({}, translations) ?? {},
      }
    }
    mutation.mutate(body, {
      onSuccess: (result) => onDone(t(role ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={role ? t('org.functionalRoles.editTitle', { name: role.name }) : t('org.functionalRoles.createTitle')}
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
            label={t('org.fields.name')}
            value={name}
            onChange={setName}
            required
            maxLength={200}
            error={showErrors ? errors.name : undefined}
          />
          <SelectField
            label={t('org.fields.jobFamily')}
            value={familyId}
            onChange={setFamilyId}
            options={familyOptions}
            emptyLabel={t('org.common.none')}
          />
          <SelectField
            label={t('org.fields.ownerUnit')}
            value={ownerId}
            onChange={setOwnerId}
            options={unitOptions}
            emptyLabel={t('org.common.none')}
            hint={t('org.functionalRoles.ownerHint')}
          />
        </div>
        <TextAreaField label={t('org.fields.description')} value={description} onChange={setDescription} maxLength={1000} />
        {role ? (
          <CheckboxField
            label={t('org.fields.activeLabel')}
            checked={active}
            onChange={setActive}
            hint={t('org.functionalRoles.inactiveHint')}
          />
        ) : null}
        <TranslationFields values={translations} onChange={setTranslations} />
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={role ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}
