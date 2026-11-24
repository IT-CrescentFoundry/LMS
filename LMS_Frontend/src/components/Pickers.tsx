import { X } from 'lucide-react'
import { useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useHasPermission } from '../features/auth/authContext'
import { PERMISSIONS } from '../features/auth/permissions'
import { useDesignationPicker, useEmployeePicker } from '../features/employees/employeeQueries'
import { localName } from '../features/organisation/names'
import { useLocations, useOrgTree, useRolePicker } from '../features/organisation/orgQueries'
import type { EmployeeRef } from '../types/training'
import { inputClassName, labelClassName } from './formStyles'
import { flattenTree } from '../lib/orgTreeOptions'

interface SelectProps {
  label: string
  value: string
  onChange: (value: string) => void
  allLabel?: string
  id?: string
}

/**
 * Organisation unit picker (needs `organisation.view`; hidden without it, because the
 * server would refuse the tree).
 */
export function UnitSelect({ label, value, onChange, allLabel }: SelectProps) {
  const { t, i18n } = useTranslation()
  const id = useId()
  const allowed = useHasPermission(PERMISSIONS.ORGANISATION_VIEW)
  const tree = useOrgTree({})
  const options = useMemo(() => flattenTree(tree.data?.nodes ?? []), [tree.data])
  if (!allowed || tree.isError) return null
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClassName()}>
        <option value="">{allLabel ?? t('picker.allUnits')}</option>
        {options.map(({ node, depth }) => (
          <option key={node.public_id} value={node.public_id}>
            {`${'  '.repeat(depth)}${localName(node, i18n.resolvedLanguage)} (${node.code})`}
          </option>
        ))}
      </select>
    </div>
  )
}

/** Location picker (needs `organisation.view`; hidden without it). */
export function LocationSelect({ label, value, onChange, allLabel }: SelectProps) {
  const { t } = useTranslation()
  const id = useId()
  const allowed = useHasPermission(PERMISSIONS.ORGANISATION_VIEW)
  const locations = useLocations(false)
  if (!allowed || locations.isError) return null
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClassName()}>
        <option value="">{allLabel ?? t('picker.allLocations')}</option>
        {(locations.data ?? []).map((location) => (
          <option key={location.public_id} value={location.public_id}>
            {location.name} ({location.code})
          </option>
        ))}
      </select>
    </div>
  )
}

/**
 * Designation picker (first page of designations from the occupational reference list).
 * A saved value missing from that page is kept and shown, never silently dropped.
 */
export function DesignationSelect({
  label,
  value,
  onChange,
  allLabel,
  current,
}: SelectProps & { current?: { public_id: string; code: string; name: string } | null }) {
  const { t } = useTranslation()
  const id = useId()
  const allowed = useHasPermission(PERMISSIONS.ORGANISATION_VIEW)
  const designations = useDesignationPicker('', allowed)
  if (!allowed || designations.isError) return null
  const items = designations.data?.items ?? []
  const missing = current && value === current.public_id && !items.some((d) => d.public_id === current.public_id)
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClassName()}>
        <option value="">{allLabel ?? t('picker.allDesignations')}</option>
        {missing ? (
          <option value={current.public_id}>
            {current.name} ({current.code})
          </option>
        ) : null}
        {items.map((designation) => (
          <option key={designation.public_id} value={designation.public_id}>
            {designation.title} ({designation.code})
          </option>
        ))}
      </select>
    </div>
  )
}

/**
 * Functional-role picker (first page of active roles from the occupational reference
 * list; needs `organisation.view`, hidden without it). A value that is no longer in
 * the list (e.g. a role deactivated later) is kept and shown, never silently dropped.
 */
export function FunctionalRoleSelect({
  label,
  value,
  onChange,
  allLabel,
  current,
}: SelectProps & { current?: { public_id: string; code: string; name: string } | null }) {
  const { t } = useTranslation()
  const id = useId()
  const allowed = useHasPermission(PERMISSIONS.ORGANISATION_VIEW)
  const roles = useRolePicker(allowed)
  if (!allowed || roles.isError) return null
  const items = (roles.data?.items ?? []).filter((role) => role.is_active)
  const missing = current && value === current.public_id && !items.some((r) => r.public_id === current.public_id)
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClassName()}>
        <option value="">{allLabel ?? t('picker.allFunctionalRoles')}</option>
        {missing ? (
          <option value={current.public_id}>
            {current.name} ({current.code})
          </option>
        ) : null}
        {items.map((role) => (
          <option key={role.public_id} value={role.public_id}>
            {role.name} ({role.code})
          </option>
        ))}
      </select>
    </div>
  )
}

/**
 * Employee search-and-select (needs `employees.view`). With `multiple`, chosen
 * employees appear as removable chips.
 */
export function EmployeePicker({
  label,
  selected,
  onChange,
  multiple = false,
}: {
  label: string
  selected: EmployeeRef[]
  onChange: (value: EmployeeRef[]) => void
  multiple?: boolean
}) {
  const { t } = useTranslation()
  const id = useId()
  const allowed = useHasPermission(PERMISSIONS.EMPLOYEES_VIEW)
  const [q, setQ] = useState('')
  const results = useEmployeePicker(q.trim(), allowed && q.trim().length >= 2)
  if (!allowed) {
    return <p className="text-sm text-slate-600">{t('picker.employeesNotPermitted')}</p>
  }
  const chosen = new Set(selected.map((e) => e.public_id))
  const pick = (employee: EmployeeRef) => {
    onChange(multiple ? [...selected, employee] : [employee])
    setQ('')
  }
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      {selected.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5" aria-label={t('picker.selected')}>
          {selected.map((employee) => (
            <li
              key={employee.public_id}
              className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-sm text-brand-900 ring-1 ring-brand-200"
            >
              {employee.name} ({employee.employee_code})
              <button
                type="button"
                onClick={() => onChange(selected.filter((e) => e.public_id !== employee.public_id))}
                aria-label={t('picker.remove', { name: employee.name })}
                className="rounded-full p-0.5 hover:bg-brand-100 focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                <X aria-hidden="true" className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <input
        id={id}
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t('picker.employeeSearch')}
        autoComplete="off"
        className={inputClassName()}
      />
      {q.trim().length >= 2 ? (
        <ul className="max-h-48 overflow-y-auto rounded-md border border-slate-200 bg-white text-sm shadow-sm">
          {results.isPending ? (
            <li className="px-3 py-2 text-slate-500">{t('common.loading')}</li>
          ) : (results.data?.items ?? []).length === 0 ? (
            <li className="px-3 py-2 text-slate-500">{t('picker.noEmployees')}</li>
          ) : (
            (results.data?.items ?? []).map((employee) => {
              const ref: EmployeeRef = {
                public_id: employee.public_id,
                employee_code: employee.employee_code,
                name: employee.display_name ?? employee.full_name,
              }
              return (
                <li key={employee.public_id}>
                  <button
                    type="button"
                    disabled={chosen.has(employee.public_id)}
                    onClick={() => pick(ref)}
                    className="w-full px-3 py-2 text-left hover:bg-slate-50 focus:bg-brand-50 focus:outline-none disabled:text-slate-400"
                  >
                    {ref.name} <span className="text-slate-500">({ref.employee_code})</span>
                  </button>
                </li>
              )
            })
          )}
        </ul>
      ) : null}
    </div>
  )
}
