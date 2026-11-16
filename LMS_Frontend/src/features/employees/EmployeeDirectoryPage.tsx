import { RotateCcw, Search, UserPlus } from 'lucide-react'
import { useId, useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router'

import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDate } from '../../lib/format'
import { isStatusFilter, STATUS_FILTERS, type EmployeeFilters } from '../../types/employee'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { Cell, HeaderCell } from '../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { ListFooter } from '../organisation/ListParts'
import { localTitle, localName } from '../organisation/names'
import { OrgPageHeader } from '../organisation/OrgParts'
import { useDesignations, useLocations, useOrgTree } from '../organisation/orgQueries'
import { ancestorIds, buildTreeIndex } from '../organisation/tree'
import { EmployeeFormDialog } from './dialogs/EmployeeDialogs'
import type { CreatedState } from './EmployeeProfileLayout'
import { useEmployees } from './employeeQueries'
import { ActionButton } from './EmployeeFormParts'
import {
  AccountBadge,
  EmployeeErrorState,
  EmployeeLink,
  EmploymentStatusBadge,
  OrgPath,
} from './EmployeeParts'

const LAYOUT = TABLE_LAYOUTS.xl

type AccountFilter = '' | 'yes' | 'no'

interface Draft {
  q: string
  status: string
  unit: string
  includeSubUnits: boolean
  location: string
  designation: string
  account: AccountFilter
  asOf: string
}

/** URL search params <-> draft form values <-> API filters. */
function draftFromParams(params: URLSearchParams): Draft {
  const account = params.get('account')
  return {
    q: params.get('q') ?? '',
    status: isStatusFilter(params.get('status')) ? (params.get('status') ?? '') : '',
    unit: params.get('unit') ?? '',
    includeSubUnits: params.get('sub') !== '0',
    location: params.get('location') ?? '',
    designation: params.get('designation') ?? '',
    account: account === 'yes' || account === 'no' ? account : '',
    asOf: params.get('as_of') ?? '',
  }
}

function paramsFromDraft(draft: Draft): URLSearchParams {
  const params = new URLSearchParams()
  if (draft.q.trim()) params.set('q', draft.q.trim())
  if (draft.status) params.set('status', draft.status)
  if (draft.unit) {
    params.set('unit', draft.unit)
    if (!draft.includeSubUnits) params.set('sub', '0')
  }
  if (draft.location) params.set('location', draft.location)
  if (draft.designation) params.set('designation', draft.designation)
  if (draft.account) params.set('account', draft.account)
  if (draft.asOf) params.set('as_of', draft.asOf)
  return params
}

function filtersFromDraft(draft: Draft): EmployeeFilters {
  const filters: EmployeeFilters = {}
  if (draft.q.trim()) filters.q = draft.q.trim()
  if (isStatusFilter(draft.status)) filters.status = draft.status
  if (draft.unit) {
    filters.unit = draft.unit
    filters.include_descendants = draft.includeSubUnits
  }
  if (draft.location) filters.location = draft.location
  if (draft.designation) filters.designation = draft.designation
  if (draft.account) filters.has_account = draft.account === 'yes'
  if (draft.asOf) filters.as_of = draft.asOf
  return filters
}

/**
 * Employee directory (`GET /employees`, permission `employees.view`). Unknown
 * employment status is its own filter value and badge; it is never shown as active.
 */
export function EmployeeDirectoryPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [searchParams, setSearchParams] = useSearchParams()
  const applied = useMemo(() => draftFromParams(searchParams), [searchParams])
  const filters = useMemo(() => filtersFromDraft(applied), [applied])
  const [draft, setDraft] = useState<Draft>(applied)
  const canManage = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const canViewOrg = useHasPermission(PERMISSIONS.ORGANISATION_VIEW)
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)

  const query = useEmployees(filters)
  useRefreshSessionOnForbidden(query.error)
  const employees = query.data?.pages.flatMap((page) => page.items) ?? []

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSearchParams(paramsFromDraft(draft))
  }

  function reset() {
    const empty = draftFromParams(new URLSearchParams())
    setDraft(empty)
    setSearchParams(new URLSearchParams())
  }

  const columns = {
    employee: t('emp.directory.columns.employee'),
    status: t('emp.directory.columns.status'),
    organisation: t('emp.directory.columns.organisation'),
    designation: t('emp.directory.columns.designation'),
    location: t('emp.directory.columns.location'),
    manager: t('emp.directory.columns.manager'),
    account: t('emp.directory.columns.account'),
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('emp.directory.title')}
        subtitle={t('emp.directory.subtitle')}
        canManage={canManage}
        actions={
          <ActionButton onClick={() => setCreating(true)}>
            <UserPlus aria-hidden="true" className="size-4" />
            {t('emp.actions.createEmployee')}
          </ActionButton>
        }
      />
      {creating ? (
        <EmployeeFormDialog
          mode="create"
          onClose={() => setCreating(false)}
          onDone={(created) => {
            setCreating(false)
            const state: CreatedState = { createdCode: created.employee_code }
            void navigate(`/employees/${created.public_id}`, { state })
          }}
        />
      ) : null}

      <DirectoryFilters
        draft={draft}
        update={update}
        onSubmit={apply}
        onReset={reset}
        canViewOrg={canViewOrg}
      />

      {applied.asOf ? (
        <p className="text-sm text-slate-600">
          {t('emp.directory.viewingAsOf', { date: formatDate(applied.asOf, language) })}
        </p>
      ) : null}

      {query.isPending ? (
        <LoadingState />
      ) : query.isError && employees.length === 0 ? (
        <EmployeeErrorState
          title={t('emp.directory.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('emp.directory.caption')}</caption>
              <thead className={LAYOUT.head}>
                <tr>
                  {Object.values(columns).map((label) => (
                    <HeaderCell key={label}>{label}</HeaderCell>
                  ))}
                </tr>
              </thead>
              <tbody className={LAYOUT.body}>
                {employees.map((employee) => (
                  <tr key={employee.public_id} className={LAYOUT.row}>
                    <Cell label={columns.employee} layout="xl">
                      <EmployeeLink employee={employee} />
                      {employee.display_name ? (
                        <span className="block text-xs text-slate-600">{employee.display_name}</span>
                      ) : null}
                    </Cell>
                    <Cell label={columns.status} layout="xl">
                      <EmploymentStatusBadge status={employee.employment_status} />
                    </Cell>
                    <Cell label={columns.organisation} layout="xl">
                      <OrgPath path={employee.path} unit={employee.primary_unit} />
                    </Cell>
                    <Cell label={columns.designation} layout="xl">
                      {employee.designation?.name ?? <span className="text-slate-500">—</span>}
                    </Cell>
                    <Cell label={columns.location} layout="xl">
                      {employee.location?.name ?? <span className="text-slate-500">—</span>}
                    </Cell>
                    <Cell label={columns.manager} layout="xl">
                      {employee.line_manager ? (
                        <EmployeeLink employee={employee.line_manager} />
                      ) : (
                        <span className="text-slate-500">{t('emp.common.none')}</span>
                      )}
                    </Cell>
                    <Cell label={columns.account} layout="xl">
                      <AccountBadge active={employee.has_active_account} />
                    </Cell>
                  </tr>
                ))}
              </tbody>
            </table>
            {employees.length === 0 ? (
              <p className="p-6 text-center text-slate-600">{t('emp.directory.empty')}</p>
            ) : null}
          </div>

          <ListFooter
            countText={t('emp.directory.count', { count: employees.length })}
            hasMore={Boolean(query.hasNextPage)}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
          />

          {query.isFetchNextPageError ? (
            <EmployeeErrorState
              title={t('emp.directory.loadError')}
              error={query.error}
              onRetry={() => void query.fetchNextPage()}
              isRetrying={query.isFetchingNextPage}
            />
          ) : null}
        </div>
      )}
    </div>
  )
}

function DirectoryFilters({
  draft,
  update,
  onSubmit,
  onReset,
  canViewOrg,
}: {
  draft: Draft
  update: <K extends keyof Draft>(key: K, value: Draft[K]) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onReset: () => void
  canViewOrg: boolean
}) {
  const { t } = useTranslation()
  const ids = {
    q: useId(),
    status: useId(),
    account: useId(),
    asOf: useId(),
  }

  return (
    <form
      role="search"
      aria-label={t('emp.directory.filters')}
      onSubmit={onSubmit}
      className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-4"
    >
      <div className="space-y-1.5 sm:col-span-2">
        <label htmlFor={ids.q} className={labelClassName}>
          {t('emp.directory.search')}
        </label>
        <input
          id={ids.q}
          type="search"
          value={draft.q}
          onChange={(event) => update('q', event.target.value)}
          maxLength={100}
          placeholder={t('emp.directory.searchPlaceholder')}
          autoComplete="off"
          className={inputClassName()}
        />
      </div>
      <div className="space-y-1.5">
        <label htmlFor={ids.status} className={labelClassName}>
          {t('emp.fields.status')}
        </label>
        <select
          id={ids.status}
          value={draft.status}
          onChange={(event) => update('status', event.target.value)}
          className={inputClassName()}
        >
          <option value="">{t('emp.directory.allStatuses')}</option>
          {STATUS_FILTERS.map((code) => (
            <option key={code} value={code}>
              {t(`emp.status.${code}`)}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor={ids.account} className={labelClassName}>
          {t('emp.directory.accountFilter')}
        </label>
        <select
          id={ids.account}
          value={draft.account}
          onChange={(event) => update('account', event.target.value as AccountFilter)}
          className={inputClassName()}
        >
          <option value="">{t('emp.directory.accountAny')}</option>
          <option value="yes">{t('emp.directory.accountYes')}</option>
          <option value="no">{t('emp.directory.accountNo')}</option>
        </select>
      </div>

      {canViewOrg ? <OrgFilterFields draft={draft} update={update} /> : null}

      <div className="space-y-1.5">
        <label htmlFor={ids.asOf} className={labelClassName}>
          {t('emp.common.asOf')}
        </label>
        <input
          id={ids.asOf}
          type="date"
          value={draft.asOf}
          onChange={(event) => update('asOf', event.target.value)}
          className={inputClassName()}
        />
      </div>

      <div className="flex flex-wrap items-end gap-2 sm:col-span-2 xl:col-span-3">
        <button type="submit" className={primaryButtonClassName}>
          <Search aria-hidden="true" className="size-4" />
          {t('admin.applyFilters')}
        </button>
        <button type="button" onClick={onReset} className={secondaryButtonClassName}>
          <RotateCcw aria-hidden="true" className="size-4" />
          {t('admin.resetFilters')}
        </button>
      </div>
    </form>
  )
}

/** Unit, designation and location filters (need `organisation.view`). */
function OrgFilterFields({
  draft,
  update,
}: {
  draft: Draft
  update: <K extends keyof Draft>(key: K, value: Draft[K]) => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const ids = { unit: useId(), sub: useId(), location: useId(), designation: useId() }
  // Filter options come from the organisation reference data (organisation.view).
  const tree = useOrgTree({ as_of: draft.asOf || undefined })
  const locations = useLocations(false)
  const designations = useDesignations({})

  const unitOptions = useMemo(() => {
    if (!tree.data) return []
    const index = buildTreeIndex(tree.data.nodes, language)
    return tree.data.nodes
      .map((node) => {
        const names = [...ancestorIds(index, node.public_id), node.public_id].map((id) => {
          const item = index.byId.get(id)
          return item ? localName(item, language) : id
        })
        return { value: node.public_id, label: `${names.join(' › ')} (${node.code})` }
      })
      .sort((a, b) => a.label.localeCompare(b.label, language))
  }, [tree.data, language])

  return (
    <>
      <div className="space-y-1.5 sm:col-span-2">
        <label htmlFor={ids.unit} className={labelClassName}>
          {t('emp.directory.unit')}
        </label>
        <select
          id={ids.unit}
          value={draft.unit}
          onChange={(event) => update('unit', event.target.value)}
          className={inputClassName()}
        >
          <option value="">{t('emp.directory.allUnits')}</option>
          {unitOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2 pt-1">
          <input
            id={ids.sub}
            type="checkbox"
            checked={draft.includeSubUnits}
            disabled={!draft.unit}
            onChange={(event) => update('includeSubUnits', event.target.checked)}
            className="size-4 rounded border-slate-300 text-brand-700 focus:ring-2 focus:ring-brand-500"
          />
          <label htmlFor={ids.sub} className="text-sm text-slate-800">
            {t('emp.directory.includeSubUnits')}
          </label>
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor={ids.designation} className={labelClassName}>
          {t('emp.fields.designation')}
        </label>
        <select
          id={ids.designation}
          value={draft.designation}
          onChange={(event) => update('designation', event.target.value)}
          className={inputClassName()}
        >
          <option value="">{t('emp.directory.any')}</option>
          {(designations.data?.pages[0]?.items ?? []).map((item) => (
            <option key={item.public_id} value={item.public_id}>
              {`${localTitle(item, language)} (${item.code})`}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor={ids.location} className={labelClassName}>
          {t('emp.fields.location')}
        </label>
        <select
          id={ids.location}
          value={draft.location}
          onChange={(event) => update('location', event.target.value)}
          className={inputClassName()}
        >
          <option value="">{t('emp.directory.any')}</option>
          {(locations.data ?? []).map((item) => (
            <option key={item.public_id} value={item.public_id}>
              {`${item.name} (${item.code})`}
            </option>
          ))}
        </select>
      </div>
    </>
  )
}
