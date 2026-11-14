import { PencilLine, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService } from '../../services/organisationService'
import type { Location } from '../../types/organisation'
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
  TextField,
  type SuccessNotice,
} from './OrgParts'
import { useLocations, useOrgMutation, useReloadAndClose } from './orgQueries'

const ADDRESS_FIELDS = ['address_line1', 'address_line2', 'city', 'state', 'postal_code'] as const

/** Physical sites (`/organisation/locations`). No location is seeded or invented. */
export function LocationsPage() {
  const { t } = useTranslation()
  const canManage = useHasPermission(PERMISSIONS.ORGANISATION_MANAGE)
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editing, setEditing] = useState<Location | 'new' | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const query = useLocations(includeInactive)
  useRefreshSessionOnForbidden(query.error)

  const locations = (query.data ?? []).filter((location) =>
    textMatches([location.code, location.name, location.city, location.state, location.country_code], search),
  )
  const columns = {
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    place: t('org.locations.columns.place'),
    timeZone: t('org.fields.timeZone'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.locations.title')}
        subtitle={t('org.locations.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.locations.create')}
          </button>
        }
      />
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <ListToolbar
        label={t('org.locations.title')}
        search={search}
        onSearch={setSearch}
        placeholder={t('org.locations.searchPlaceholder')}
        includeInactive={includeInactive}
        onIncludeInactive={setIncludeInactive}
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <AdminErrorState
          title={t('org.locations.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('org.locations.caption')}</caption>
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
              {locations.map((location) => (
                <tr key={location.public_id} className={TABLE_LAYOUTS.md.row}>
                  <Cell label={columns.name}>
                    <span className="font-medium text-slate-900">{location.name}</span>
                  </Cell>
                  <Cell label={columns.code}>
                    <span className="font-mono">{location.code}</span>
                  </Cell>
                  <Cell label={columns.place}>
                    {[location.city, location.state, location.country_code].filter(Boolean).join(', ') || '—'}
                  </Cell>
                  <Cell label={columns.timeZone}>{location.time_zone ?? '—'}</Cell>
                  <Cell label={columns.status}>
                    <ActiveBadge active={location.is_active} />
                  </Cell>
                  {canManage ? (
                    <Cell label={columns.actions}>
                      <RowButton
                        onClick={() => setEditing(location)}
                        label={t('org.actions.editNamed', { name: location.name })}
                      >
                        <PencilLine aria-hidden="true" className="size-4" />
                        {t('org.actions.edit')}
                      </RowButton>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {locations.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.locations.empty')}</p> : null}
        </div>
      )}

      {editing !== null ? (
        <LocationDialog
          location={editing === 'new' ? undefined : editing}
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

function LocationDialog({
  location,
  onClose,
  onDone,
}: {
  location?: Location
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const initial: Record<string, string> = {
    code: location?.code ?? '',
    name: location?.name ?? '',
    country_code: location?.country_code ?? '',
    time_zone: location?.time_zone ?? '',
  }
  for (const field of ADDRESS_FIELDS) initial[field] = location?.[field] ?? ''
  const [values, setValues] = useState(initial)
  const [active, setActive] = useState(location?.is_active ?? true)
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadAndClose(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    location
      ? organisationService.updateLocation(location.public_id, { ...body, version: location.version })
      : organisationService.createLocation(body as { code: string; name: string }),
  )
  const set = (field: string) => (value: string) => setValues((current) => ({ ...current, [field]: value }))

  const required = t('org.errors.required')
  const errors = {
    code: values.code.trim() === '' ? required : undefined,
    name: values.name.trim() === '' ? required : undefined,
    country:
      values.country_code.trim() !== '' && !/^[A-Za-z]{2}$/.test(values.country_code.trim())
        ? t('org.errors.countryCode')
        : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name || errors.country) return
    const body: Record<string, unknown> = {}
    for (const [field, raw] of Object.entries(values)) {
      const value = raw.trim() === '' ? null : raw.trim()
      const previous = location ? (location[field as keyof Location] ?? null) : null
      if (!location || value !== previous) body[field] = value
    }
    if (location && active !== location.is_active) body.is_active = active
    if (location && Object.keys(body).length === 0) {
      onClose()
      return
    }
    mutation.mutate(body, {
      onSuccess: (result) =>
        onDone(t(location ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={location ? t('org.locations.editTitle', { name: location.name }) : t('org.locations.createTitle')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('org.fields.code')}
            value={values.code}
            onChange={set('code')}
            required
            maxLength={50}
            hint={t('org.hints.code')}
            error={showErrors ? errors.code : undefined}
            autoFocus
          />
          <TextField
            label={t('org.fields.name')}
            value={values.name}
            onChange={set('name')}
            required
            maxLength={200}
            error={showErrors ? errors.name : undefined}
          />
          <TextField label={t('org.fields.addressLine1')} value={values.address_line1} onChange={set('address_line1')} maxLength={200} />
          <TextField label={t('org.fields.addressLine2')} value={values.address_line2} onChange={set('address_line2')} maxLength={200} />
          <TextField label={t('org.fields.city')} value={values.city} onChange={set('city')} maxLength={100} />
          <TextField label={t('org.fields.state')} value={values.state} onChange={set('state')} maxLength={100} />
          <TextField label={t('org.fields.postalCode')} value={values.postal_code} onChange={set('postal_code')} maxLength={20} />
          <TextField
            label={t('org.fields.country')}
            value={values.country_code}
            onChange={set('country_code')}
            maxLength={2}
            hint={t('org.hints.country')}
            error={showErrors ? errors.country : undefined}
          />
          <TextField
            label={t('org.fields.timeZone')}
            value={values.time_zone}
            onChange={set('time_zone')}
            maxLength={64}
            hint={t('org.hints.timeZone')}
            placeholder="Asia/Kolkata"
          />
        </div>
        {location ? (
          <CheckboxField label={t('org.fields.activeLabel')} checked={active} onChange={setActive} hint={t('org.locations.inactiveHint')} />
        ) : null}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={location ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}
