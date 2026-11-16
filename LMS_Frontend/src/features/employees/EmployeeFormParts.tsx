import { CircleAlert, CircleCheck, RefreshCw, TriangleAlert, X } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import type { EmployeeWarning } from '../../types/employee'
import type { Ref } from '../../types/organisation'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { localName, localTitle } from '../organisation/names'
import { SelectField, TextField, type SelectOption } from '../organisation/OrgParts'
import { useLocations, useOrgTree, useRanked } from '../organisation/orgQueries'
import { ancestorIds, buildTreeIndex } from '../organisation/tree'
import { describeEmployeeError, isEmployeeWarningCode } from './employeeErrors'
import { useEmployeeErrorMessage } from './employeeErrorMessage'
import { useDesignationPicker, useEmployeePicker } from './employeeQueries'

// --------------------------------------------------------------- feedback



export interface EmployeeNoticeValue {
  message: string
  warnings: EmployeeWarning[]
}

/** Success feedback with advisory warnings (e.g. a unit type not meant for people). */
export function EmployeeNotice({ notice, onDismiss }: { notice: EmployeeNoticeValue; onDismiss: () => void }) {
  const { t } = useTranslation()
  const hasWarnings = notice.warnings.length > 0
  return (
    <div
      role="status"
      className={`flex gap-3 rounded-lg border p-3 text-sm ${
        hasWarnings ? 'border-amber-200 bg-amber-50 text-amber-950' : 'border-emerald-200 bg-emerald-50 text-emerald-950'
      }`}
    >
      {hasWarnings ? (
        <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-amber-700" />
      ) : (
        <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-emerald-700" />
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-medium break-words">{notice.message}</p>
        {hasWarnings ? (
          <ul className="list-disc space-y-0.5 pl-5">
            {notice.warnings.map((warning, index) => (
              <li key={`${warning.code}-${index}`}>
                {isEmployeeWarningCode(warning.code)
                  ? t(`emp.warnings.${warning.code}`)
                  : t('emp.warnings.generic', { code: warning.code })}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={t('org.actions.dismiss')}
        className="-m-1 self-start rounded p-1 hover:bg-black/5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </div>
  )
}

/**
 * A rejected change with its translated reason (the server's English text is
 * never shown). Separation blockers are listed; a version conflict offers a reload
 * instead of overwriting; a 403 re-reads the session so the screen catches up.
 */
export function EmployeeChangeError({ error, onReload }: { error: unknown; onReload?: () => void }) {
  const { t } = useTranslation()
  const message = useEmployeeErrorMessage()
  useRefreshSessionOnForbidden(error)
  const described = describeEmployeeError(error)
  const conflict = described.kind === 'code' && described.code === 'version_conflict'
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
      <div className="flex gap-2">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-red-600" />
        <div className="min-w-0 space-y-2">
          <p className="font-medium">{t('org.errors.title')}</p>
          <p className="break-words">{message(described)}</p>
          {described.kind === 'code' && described.blockers.length > 0 ? (
            <div>
              <p className="font-medium">{t('emp.separation.blockersTitle')}</p>
              <ul className="list-disc space-y-0.5 pl-5">
                {described.blockers.map((blocker, index) => (
                  <li key={`${blocker.rawType}-${blocker.label}-${index}`} className="break-words">
                    {t(`emp.errors.blockers.${blocker.type}`, { code: blocker.label })}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {described.kind === 'code' && described.requestId ? (
            <p className="text-xs text-red-800">{t('auth.errors.reference', { requestId: described.requestId })}</p>
          ) : null}
          {conflict && onReload ? (
            <button
              type="button"
              onClick={onReload}
              className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 font-medium text-red-900 shadow-sm ring-1 ring-red-200 hover:bg-red-100 focus:ring-2 focus:ring-red-500 focus:outline-none"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              {t('org.actions.reload')}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

/** Primary action button for section headers ("Add assignment", ...). */
export function ActionButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={primaryButtonClassName}>
      {children}
    </button>
  )
}

// ----------------------------------------------------------------- fields

/** "Last day in effect": the form's end date. Converted to the exclusive end on submit. */
export function LastDayField({
  value,
  onChange,
  required = false,
  error,
  autoFocus,
}: {
  value: string
  onChange: (value: string) => void
  required?: boolean
  error?: string
  autoFocus?: boolean
}) {
  const { t } = useTranslation()
  return (
    <TextField
      label={t('emp.fields.lastDayInEffect')}
      type="date"
      value={value}
      onChange={onChange}
      required={required}
      hint={t('emp.hints.lastDay')}
      error={error}
      autoFocus={autoFocus}
    />
  )
}

function withCurrent(options: SelectOption[], current: Ref | null | undefined): SelectOption[] {
  if (!current || options.some((option) => option.value === current.public_id)) return options
  return [{ value: current.public_id, label: `${current.name} (${current.code})` }, ...options]
}

/**
 * Organisation unit chooser: filter text + list of units that are active on
 * `asOf` (path labels as on that date). The current unit stays selectable when
 * correcting an older record.
 */
export function UnitSelect({
  label,
  value,
  onChange,
  asOf,
  current,
  required = false,
  error,
  emptyLabel,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  asOf: string
  current?: Ref | null
  required?: boolean
  error?: string
  emptyLabel?: string
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [filter, setFilter] = useState('')
  const tree = useOrgTree({ as_of: /^\d{4}-\d{2}-\d{2}$/.test(asOf) ? asOf : undefined })
  const options = useMemo(() => {
    if (!tree.data) return []
    const index = buildTreeIndex(tree.data.nodes, language)
    return tree.data.nodes
      .filter((node) => node.status === 'active')
      .map((node) => {
        const names = [...ancestorIds(index, node.public_id), node.public_id].map((id) => {
          const item = index.byId.get(id)
          return item ? localName(item, language) : id
        })
        return { value: node.public_id, label: `${names.join(' › ')} (${node.code})` }
      })
      .sort((a, b) => a.label.localeCompare(b.label, language))
  }, [tree.data, language])
  const needle = filter.trim().toLocaleLowerCase()
  const visible = withCurrent(options, current).filter(
    (option) => option.value === value || needle === '' || option.label.toLocaleLowerCase().includes(needle),
  )
  return (
    <div className="space-y-2 sm:col-span-2">
      <TextField label={t('emp.fields.unitFilter')} value={filter} onChange={setFilter} maxLength={100} />
      <SelectField
        label={label}
        value={value}
        onChange={onChange}
        options={visible}
        emptyLabel={emptyLabel ?? t('org.common.choose')}
        required={required}
        error={error}
      />
    </div>
  )
}

/** Designation chooser with server search (titles in the user's language). */
export function DesignationSelect({
  value,
  onChange,
  current,
}: {
  value: string
  onChange: (value: string) => void
  current?: Ref | null
}) {
  const { t, i18n } = useTranslation()
  const [filter, setFilter] = useState('')
  const query = useDesignationPicker(filter.trim())
  const options = (query.data?.items ?? []).map((item) => ({
    value: item.public_id,
    label: `${localTitle(item, i18n.resolvedLanguage)} (${item.code})`,
  }))
  return (
    <div className="space-y-2">
      <TextField label={t('emp.fields.designationFilter')} value={filter} onChange={setFilter} maxLength={100} />
      <SelectField
        label={t('emp.fields.designation')}
        value={value}
        onChange={onChange}
        options={withCurrent(options, current)}
        emptyLabel={t('org.common.none')}
      />
    </div>
  )
}

export function RankedSelect({
  kind,
  value,
  onChange,
  current,
}: {
  kind: 'grades' | 'levels'
  value: string
  onChange: (value: string) => void
  current?: Ref | null
}) {
  const { t } = useTranslation()
  const query = useRanked(kind, false)
  const options = (query.data ?? []).map((item) => ({ value: item.public_id, label: `${item.name} (${item.code})` }))
  return (
    <SelectField
      label={kind === 'grades' ? t('emp.fields.grade') : t('emp.fields.level')}
      value={value}
      onChange={onChange}
      options={withCurrent(options, current)}
      emptyLabel={t('org.common.none')}
    />
  )
}

export function LocationSelect({
  label,
  value,
  onChange,
  current,
}: {
  label?: string
  value: string
  onChange: (value: string) => void
  current?: Ref | null
}) {
  const { t } = useTranslation()
  const query = useLocations(false)
  const options = (query.data ?? []).map((item) => ({ value: item.public_id, label: `${item.name} (${item.code})` }))
  return (
    <SelectField
      label={label ?? t('emp.fields.location')}
      value={value}
      onChange={onChange}
      options={withCurrent(options, current)}
      emptyLabel={t('org.common.none')}
    />
  )
}

/**
 * Employee chooser (server search by code or name). The employee being edited is
 * not offered; every other rule (e.g. a separated manager) is the server's.
 */
export function EmployeeSelect({
  label,
  value,
  onChange,
  excludeId,
  required = false,
  error,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  excludeId: string
  required?: boolean
  error?: string
}) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState('')
  const query = useEmployeePicker(filter.trim(), true)
  const options = (query.data?.items ?? [])
    .filter((item) => item.public_id !== excludeId)
    .map((item) => ({
      value: item.public_id,
      label: `${item.employee_code} · ${item.full_name} — ${
        item.employment_status ? t(`emp.status.${item.employment_status}`) : t('emp.status.unknown')
      }`,
    }))
  return (
    <div className="space-y-2">
      <TextField
        label={t('emp.fields.employeeSearch')}
        value={filter}
        onChange={setFilter}
        maxLength={100}
        placeholder={t('emp.directory.searchPlaceholder')}
        autoFocus
      />
      <SelectField
        label={label}
        value={value}
        onChange={onChange}
        options={options}
        size={6}
        required={required}
        error={error}
        hint={t('emp.hints.employeeSearch')}
      />
    </div>
  )
}
