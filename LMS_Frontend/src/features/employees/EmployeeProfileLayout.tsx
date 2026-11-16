import { ChevronRight, Eye, PencilLine, UserCheck, UserMinus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { LoadingState } from '../../components/LoadingState'
import { formatDate } from '../../lib/format'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS, type PermissionCode } from '../auth/permissions'
import { EmployeeFormDialog, StatusDialog } from './dialogs/EmployeeDialogs'
import { SeparationDialog } from './dialogs/SeparationDialog'
import { useEmployee } from './employeeQueries'
import { EmployeeNotice, type EmployeeNoticeValue } from './EmployeeFormParts'
import type { ProfileContext } from './profileContext'
import { AccountBadge, AsOfControl, EmployeeErrorState, EmploymentStatusBadge } from './EmployeeParts'

type HeaderDialog = 'edit' | 'status' | 'separate' | null

const HEADER_BUTTON =
  'inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm ring-1 ring-slate-300 hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none'
const DANGER_HEADER_BUTTON =
  'inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-2 text-sm font-medium text-red-800 shadow-sm ring-1 ring-red-300 hover:bg-red-50 focus:ring-2 focus:ring-red-500 focus:outline-none'

/** Navigation state set after creating an employee (shown once on the profile). */
export interface CreatedState {
  createdCode?: string
}

type TabLabelKey =
  | 'emp.tabs.overview'
  | 'emp.tabs.assignments'
  | 'emp.tabs.roles'
  | 'emp.tabs.responsibilities'
  | 'emp.tabs.reporting'
  | 'emp.tabs.account'
  | 'emp.tabs.history'

interface Tab {
  path: string
  labelKey: TabLabelKey
  permission: PermissionCode
}

const TABS: readonly Tab[] = [
  { path: '', labelKey: 'emp.tabs.overview', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: 'assignments', labelKey: 'emp.tabs.assignments', permission: PERMISSIONS.EMPLOYEES_HISTORY_VIEW },
  { path: 'roles', labelKey: 'emp.tabs.roles', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: 'responsibilities', labelKey: 'emp.tabs.responsibilities', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: 'reporting', labelKey: 'emp.tabs.reporting', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: 'account', labelKey: 'emp.tabs.account', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: 'history', labelKey: 'emp.tabs.history', permission: PERMISSIONS.EMPLOYEES_HISTORY_VIEW },
]

/**
 * Employee profile shell: header, as-of date and the tab links. Tabs are routes
 * (deep-linkable); a tab whose permission the user lacks is not linked, and its
 * route shows the "forbidden" page. The as-of date lives in the URL (`?as_of=`).
 */
export function EmployeeProfileLayout() {
  const { t, i18n } = useTranslation()
  const { employeeId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const createdCode = (location.state as CreatedState | null)?.createdCode
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(
    createdCode ? { message: t('emp.messages.created', { code: createdCode }), warnings: [] } : null,
  )
  const [dialog, setDialog] = useState<HeaderDialog>(null)
  const asOfParam = searchParams.get('as_of') ?? ''
  const asOf = /^\d{4}-\d{2}-\d{2}$/.test(asOfParam) ? asOfParam : undefined
  const query = useEmployee(employeeId, asOf)
  useRefreshSessionOnForbidden(query.error)
  const canManage = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const canHistory = useHasPermission(PERMISSIONS.EMPLOYEES_HISTORY_VIEW)
  const search = asOf ? `?as_of=${asOf}` : ''

  function dismissNotice() {
    setNotice(null)
    // Drop the one-off "created" state so a reload does not show it again.
    if (createdCode) void navigate(`${location.pathname}${location.search}`, { replace: true, state: null })
  }

  function changeAsOf(value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('as_of', value)
    else next.delete('as_of')
    setSearchParams(next, { replace: true })
  }

  const breadcrumb = (
    <nav aria-label={t('emp.profile.breadcrumb')}>
      <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-600">
        <li>
          <Link
            to="/employees"
            className="rounded hover:text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
          >
            {t('nav.employees')}
          </Link>
        </li>
        <li aria-hidden="true">
          <ChevronRight className="size-4 text-slate-400" />
        </li>
        <li aria-current="page" className="font-mono font-medium text-slate-900">
          {query.data?.employee_code ?? '…'}
        </li>
      </ol>
    </nav>
  )

  if (query.isPending) {
    return (
      <div className="space-y-6">
        {breadcrumb}
        <LoadingState />
      </div>
    )
  }
  if (query.isError) {
    return (
      <div className="space-y-6">
        {breadcrumb}
        <EmployeeErrorState
          title={t('emp.profile.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      </div>
    )
  }

  const employee = query.data
  const visibleTabs = TABS.filter(
    (tab) => tab.permission !== PERMISSIONS.EMPLOYEES_HISTORY_VIEW || canHistory,
  )
  const context: ProfileContext = { employee, asOf }

  return (
    <div className="space-y-6">
      {breadcrumb}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{employee.full_name}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
            <span className="font-mono font-medium">{employee.employee_code}</span>
            <EmploymentStatusBadge status={employee.employment_status} />
            <AccountBadge active={employee.has_active_account} />
            {canManage ? null : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
                <Eye aria-hidden="true" className="size-3.5" />
                {t('admin.readOnly')}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          {canManage ? (
            <div className="flex flex-wrap gap-2" role="group" aria-label={t('emp.profile.actions')}>
              <button type="button" onClick={() => setDialog('edit')} className={HEADER_BUTTON}>
                <PencilLine aria-hidden="true" className="size-4" />
                {t('emp.actions.editDetails')}
              </button>
              <button type="button" onClick={() => setDialog('status')} className={HEADER_BUTTON}>
                <UserCheck aria-hidden="true" className="size-4" />
                {t('emp.actions.changeStatus')}
              </button>
              {employee.employment_status !== 'separated' ? (
                <button type="button" onClick={() => setDialog('separate')} className={DANGER_HEADER_BUTTON}>
                  <UserMinus aria-hidden="true" className="size-4" />
                  {t('emp.actions.separate')}
                </button>
              ) : null}
            </div>
          ) : null}
          <AsOfControl value={asOf ?? ''} onChange={changeAsOf} />
        </div>
      </header>
      {notice ? <EmployeeNotice notice={notice} onDismiss={dismissNotice} /> : null}
      <p className="text-sm text-slate-600">
        {t('emp.profile.viewingAsOf', { date: formatDate(employee.as_of, i18n.resolvedLanguage) })}
      </p>

      {/* Wrapping links: every tab stays visible at every width (no hidden scroll). */}
      <nav aria-label={t('emp.profile.sections')}>
        <ul className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
          {visibleTabs.map((tab) => (
            <li key={tab.path}>
              <NavLink
                to={`/employees/${employee.public_id}${tab.path ? `/${tab.path}` : ''}${search}`}
                end
                className={({ isActive }) =>
                  `inline-block rounded-full px-3 py-1.5 text-sm font-medium focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 focus:outline-none ${
                    isActive
                      ? 'bg-brand-700 text-white shadow-sm'
                      : 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                {t(tab.labelKey)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <Outlet context={context} />

      {dialog === 'edit' ? (
        <EmployeeFormDialog
          mode="edit"
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(saved) => {
            setDialog(null)
            setNotice({ message: t('emp.messages.corrected', { code: saved.employee_code }), warnings: [] })
          }}
        />
      ) : null}
      {dialog === 'status' ? (
        <StatusDialog
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(saved) => {
            setDialog(null)
            setNotice({
              message: t('emp.messages.statusChanged', {
                status: saved.employment_status ? t(`emp.status.${saved.employment_status}`) : t('emp.status.unknown'),
              }),
              warnings: [],
            })
          }}
        />
      ) : null}
      {dialog === 'separate' ? (
        <SeparationDialog
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(_saved, lastWorkingDay) => {
            setDialog(null)
            setNotice({
              message: t('emp.messages.separated', { date: formatDate(lastWorkingDay, i18n.resolvedLanguage) }),
              warnings: [],
            })
          }}
        />
      ) : null}
    </div>
  )
}
