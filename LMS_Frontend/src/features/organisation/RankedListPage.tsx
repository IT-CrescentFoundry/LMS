import { PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService } from '../../services/organisationService'
import type { RankedItem, RankedKind } from '../../types/organisation'
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
  InfoNote,
  NoticeBanner,
  OrgPageHeader,
  RowButton,
  TextField,
  type SuccessNotice,
} from './OrgParts'
import { useOrgMutation, useRanked, useReloadAndClose } from './orgQueries'

/** `/organisation/grades` */
export function GradesPage() {
  return <RankedListPage kind="grades" />
}

/** `/organisation/levels` */
export function LevelsPage() {
  return <RankedListPage kind="levels" />
}

/**
 * Grades (`/organisation/grades`) and levels (`/organisation/levels`): two
 * separate, optional lists. No relationship between them is assumed (Q-45).
 */
export function RankedListPage({ kind }: { kind: RankedKind }) {
  const { t } = useTranslation()
  const canManage = useHasPermission(PERMISSIONS.DESIGNATIONS_MANAGE)
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editing, setEditing] = useState<RankedItem | 'new' | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useRanked(kind, includeInactive)
  useRefreshSessionOnForbidden(query.error)
  const items = (query.data ?? []).filter((item) => textMatches([item.code, item.name], search))
  const columns = {
    rank: t('org.fields.rank'),
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t(`org.${kind}.title`)}
        subtitle={t(`org.${kind}.subtitle`)}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t(`org.${kind}.create`)}
          </button>
        }
      />
      <InfoNote>{t('org.ranked.independent')}</InfoNote>
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t(`org.${kind}.title`)}
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
          title={t(`org.${kind}.loadError`)}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t(`org.${kind}.title`)}</caption>
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
              {items.map((item) => (
                <tr key={item.public_id} className={TABLE_LAYOUTS.md.row}>
                  <Cell label={columns.rank}>{item.rank ?? '—'}</Cell>
                  <Cell label={columns.name}>
                    <span className="font-medium text-slate-900">{item.name}</span>
                  </Cell>
                  <Cell label={columns.code}>
                    <span className="font-mono">{item.code}</span>
                  </Cell>
                  <Cell label={columns.status}>
                    <ActiveBadge active={item.is_active} />
                  </Cell>
                  {canManage ? (
                    <Cell label={columns.actions}>
                      <RowButton onClick={() => setEditing(item)} label={t('org.actions.editNamed', { name: item.name })}>
                        <PencilLine aria-hidden="true" className="size-4" />
                        {t('org.actions.edit')}
                      </RowButton>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 ? <p className="p-6 text-center text-slate-600">{t(`org.${kind}.empty`)}</p> : null}
        </div>
      )}
      {editing !== null ? (
        <RankedDialog
          kind={kind}
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

function RankedDialog({
  kind,
  item,
  onClose,
  onDone,
}: {
  kind: RankedKind
  item?: RankedItem
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const [code, setCode] = useState(item?.code ?? '')
  const [name, setName] = useState(item?.name ?? '')
  const [rank, setRank] = useState(item?.rank === null || item?.rank === undefined ? '' : String(item.rank))
  const [active, setActive] = useState(item?.is_active ?? true)
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    item
      ? organisationService.updateRanked(kind, item.public_id, { ...body, version: item.version })
      : organisationService.createRanked(kind, body),
  )
  const rankValue = rank.trim() === '' ? null : Number(rank)
  const errors = {
    code: code.trim() === '' ? t('org.errors.required') : undefined,
    name: name.trim() === '' ? t('org.errors.required') : undefined,
    rank: rankValue !== null && (!Number.isInteger(rankValue) || rankValue < 0) ? t('org.errors.wholeNumber') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name || errors.rank) return
    let body: Record<string, unknown> = { code: code.trim(), name: name.trim(), rank: rankValue }
    if (item) {
      body = {}
      if (code.trim() !== item.code) body.code = code.trim()
      if (name.trim() !== item.name) body.name = name.trim()
      if (rankValue !== item.rank) body.rank = rankValue
      if (active !== item.is_active) body.is_active = active
      if (Object.keys(body).length === 0) {
        onClose()
        return
      }
    }
    mutation.mutate(body, {
      onSuccess: (result) => onDone(t(item ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={item ? t(`org.${kind}.editTitle`, { name: item.name }) : t(`org.${kind}.createTitle`)}
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
          maxLength={100}
          error={showErrors ? errors.name : undefined}
        />
        <TextField
          label={t('org.fields.rank')}
          type="number"
          inputMode="numeric"
          value={rank}
          onChange={setRank}
          hint={t('org.hints.rank')}
          error={showErrors ? errors.rank : undefined}
        />
        {item ? (
          <CheckboxField label={t('org.fields.activeLabel')} checked={active} onChange={setActive} hint={t('org.hints.inactive')} />
        ) : null}
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
