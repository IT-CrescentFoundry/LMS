import { PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService, translationChanges } from '../../services/organisationService'
import type { ListFilters, Responsibility } from '../../types/organisation'
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
  TextAreaField,
  TextField,
  TranslationFields,
  type SuccessNotice,
} from './OrgParts'
import { useOrgMutation, useReloadAndClose, useResponsibilities } from './orgQueries'

/**
 * Responsibilities catalogue (`/organisation/responsibilities`). A responsibility
 * never grants LMS permissions or practical authorisation.
 */
export function ResponsibilitiesPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManage = useHasPermission(PERMISSIONS.RESPONSIBILITIES_MANAGE)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<ListFilters>({})
  const [editing, setEditing] = useState<Responsibility | 'new' | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useResponsibilities(filters)
  useRefreshSessionOnForbidden(query.error)
  const items = query.data?.pages.flatMap((page) => page.items) ?? []
  const columns = {
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    category: t('org.fields.category'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.responsibilities.title')}
        subtitle={t('org.responsibilities.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.responsibilities.create')}
          </button>
        }
      />
      <InfoNote>{t('org.responsibilities.notAuthorisation')}</InfoNote>
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t('org.responsibilities.title')}
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
          title={t('org.responsibilities.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('org.responsibilities.title')}</caption>
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
                {items.map((item) => {
                  const name = localName(item, language)
                  return (
                    <tr key={item.public_id} className={TABLE_LAYOUTS.md.row}>
                      <Cell label={columns.name}>
                        <span className="font-medium text-slate-900">{name}</span>
                        {item.description ? <span className="block text-xs text-slate-600">{item.description}</span> : null}
                      </Cell>
                      <Cell label={columns.code}>
                        <span className="font-mono">{item.code}</span>
                      </Cell>
                      <Cell label={columns.category}>{item.category ?? '—'}</Cell>
                      <Cell label={columns.status}>
                        <ActiveBadge active={item.is_active} />
                      </Cell>
                      {canManage ? (
                        <Cell label={columns.actions}>
                          <RowButton onClick={() => setEditing(item)} label={t('org.actions.editNamed', { name })}>
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
            {items.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.responsibilities.empty')}</p> : null}
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
        <ResponsibilityDialog
          item={editing === 'new' ? undefined : editing}
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

function ResponsibilityDialog({
  item,
  onClose,
  onDone,
}: {
  item?: Responsibility
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const [code, setCode] = useState(item?.code ?? '')
  const [name, setName] = useState(item?.name ?? '')
  const [description, setDescription] = useState(item?.description ?? '')
  const [category, setCategory] = useState(item?.category ?? '')
  const [active, setActive] = useState(item?.is_active ?? true)
  const [translations, setTranslations] = useState<Record<string, string>>({ ...(item?.translations ?? {}) })
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    item
      ? organisationService.updateResponsibility(item.public_id, { ...body, version: item.version })
      : organisationService.createResponsibility(body),
  )
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
      category: category.trim() === '' ? null : category.trim(),
    }
    let body: Record<string, unknown>
    if (item) {
      body = {}
      if (values.code !== item.code) body.code = values.code
      if (values.name !== item.name) body.name = values.name
      if (values.description !== item.description) body.description = values.description
      if (values.category !== item.category) body.category = values.category
      if (active !== item.is_active) body.is_active = active
      const changes = translationChanges(item.translations, translations)
      if (changes) body.translations = changes
      if (Object.keys(body).length === 0) {
        onClose()
        return
      }
    } else {
      body = { ...values, translations: translationChanges({}, translations) ?? {} }
    }
    mutation.mutate(body, {
      onSuccess: (result) => onDone(t(item ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={item ? t('org.responsibilities.editTitle', { name: item.name }) : t('org.responsibilities.createTitle')}
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
          <TextField
            label={t('org.fields.category')}
            value={category}
            onChange={setCategory}
            maxLength={50}
            hint={t('org.responsibilities.categoryHint')}
          />
        </div>
        <TextAreaField label={t('org.fields.description')} value={description} onChange={setDescription} maxLength={1000} />
        {item ? (
          <CheckboxField label={t('org.fields.activeLabel')} checked={active} onChange={setActive} hint={t('org.hints.inactive')} />
        ) : null}
        <TranslationFields values={translations} onChange={setTranslations} />
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={item ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}
