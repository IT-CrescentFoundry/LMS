import { UserCog } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { formatDate } from '../../../lib/format'
import type { ReportingRecord } from '../../../types/employee'
import { Cell, HeaderCell } from '../../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../../admin/tableLayouts'
import { useHasPermission } from '../../auth/authContext'
import { PERMISSIONS } from '../../auth/permissions'
import { InfoNote, RowButton } from '../../organisation/OrgParts'
import { EndReportingDialog, SetManagerDialog } from '../dialogs/ReportingAccountDialogs'
import { useReporting } from '../employeeQueries'
import { ActionButton, EmployeeNotice, type EmployeeNoticeValue } from '../EmployeeFormParts'
import { useProfile } from '../profileContext'
import { EmployeeErrorState, EmployeeLink, EmploymentStatusBadge, RecordPeriod } from '../EmployeeParts'

const LAYOUT = TABLE_LAYOUTS.md

/** Line manager(s) and direct reports on the selected date, plus the full history. */
export function ReportingTab() {
  const { t, i18n } = useTranslation()
  const { employee, asOf } = useProfile()
  const query = useReporting(employee.public_id, asOf)
  const canManage = useHasPermission(PERMISSIONS.REPORTING_LINES_MANAGE)
  const [dialog, setDialog] = useState<{ kind: 'set' } | { kind: 'end'; record: ReportingRecord } | null>(null)
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(null)

  function done(message: string) {
    setDialog(null)
    setNotice({ message, warnings: [] })
  }

  if (query.isPending) return <LoadingState />
  if (query.isError) {
    return (
      <EmployeeErrorState
        title={t('emp.reporting.loadError')}
        error={query.error}
        onRetry={() => void query.refetch()}
        isRetrying={query.isFetching}
      />
    )
  }
  const data = query.data
  const date = formatDate(data.as_of, i18n.resolvedLanguage)
  // The open line-manager relationship (whatever the viewed date): the one a new manager replaces.
  const current =
    data.history.find((record) => record.effective_to === null && record.relationship_type.code === 'LINE_MANAGER') ??
    null

  return (
    <div className="space-y-6">
      <InfoNote>{t('emp.reporting.note')}</InfoNote>
      {notice ? <EmployeeNotice notice={notice} onDismiss={() => setNotice(null)} /> : null}
      {canManage ? (
        <div className="flex flex-wrap justify-end">
          <ActionButton onClick={() => setDialog({ kind: 'set' })}>
            <UserCog aria-hidden="true" className="size-4" />
            {current ? t('emp.actions.changeManager') : t('emp.actions.setManager')}
          </ActionButton>
        </div>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="emp-managers" className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 id="emp-managers" className="text-lg font-semibold text-slate-900">
            {t('emp.reporting.managers', { date })}
          </h2>
          <PeopleList records={data.managers} person="manager" empty={t('emp.reporting.noManager')} />
        </section>
        <section aria-labelledby="emp-reports" className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 id="emp-reports" className="text-lg font-semibold text-slate-900">
            {t('emp.reporting.directReports', { date })}
          </h2>
          <PeopleList records={data.direct_reports} person="employee" empty={t('emp.reporting.noReports')} />
        </section>
      </div>
      <ReportingHistory
        records={data.history}
        onEnd={canManage ? (record) => setDialog({ kind: 'end', record }) : undefined}
      />

      {dialog?.kind === 'set' ? (
        <SetManagerDialog
          employee={employee}
          current={current}
          onClose={() => setDialog(null)}
          onDone={(record) =>
            done(
              t('emp.messages.managerSet', {
                manager: `${record.manager.employee_code} · ${record.manager.full_name}`,
                date: record.effective_from ? formatDate(record.effective_from, i18n.resolvedLanguage) : '',
              }),
            )
          }
        />
      ) : null}
      {dialog?.kind === 'end' ? (
        <EndReportingDialog
          employee={employee}
          record={dialog.record}
          onClose={() => setDialog(null)}
          onDone={(lastDay) =>
            done(
              t('emp.messages.reportingEnded', {
                manager: dialog.record.manager.full_name,
                date: formatDate(lastDay, i18n.resolvedLanguage),
              }),
            )
          }
        />
      ) : null}
    </div>
  )
}

function PeopleList({
  records,
  person,
  empty,
}: {
  records: readonly ReportingRecord[]
  person: 'manager' | 'employee'
  empty: string
}) {
  const { t } = useTranslation()
  if (records.length === 0) return <p className="text-sm text-slate-600">{empty}</p>
  return (
    <ul className="divide-y divide-slate-100">
      {records.map((record) => (
        <li key={record.public_id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
          <EmployeeLink employee={record[person]} />
          <EmploymentStatusBadge status={record[person].employment_status} />
          <span className="text-xs text-slate-600">
            {record.relationship_type.code === 'LINE_MANAGER'
              ? t('emp.reporting.lineManagerType')
              : record.relationship_type.name}
          </span>
        </li>
      ))}
    </ul>
  )
}

function ReportingHistory({
  records,
  onEnd,
}: {
  records: readonly ReportingRecord[]
  onEnd?: (record: ReportingRecord) => void
}) {
  const { t } = useTranslation()
  const columns = {
    manager: t('emp.reporting.columns.manager'),
    type: t('emp.reporting.columns.type'),
    period: t('emp.common.period'),
    reason: t('emp.common.reason'),
    ...(onEnd ? { actions: t('emp.common.actions') } : {}),
  }
  return (
    <section aria-labelledby="emp-reporting-history" className="space-y-3">
      <h2 id="emp-reporting-history" className="text-lg font-semibold text-slate-900">
        {t('emp.reporting.history')}
      </h2>
      <div className={TABLE_CONTAINER}>
        <table className="w-full text-left text-sm">
          <caption className="sr-only">{t('emp.reporting.history')}</caption>
          <thead className={LAYOUT.head}>
            <tr>
              {Object.values(columns).map((label) => (
                <HeaderCell key={label}>{label}</HeaderCell>
              ))}
            </tr>
          </thead>
          <tbody className={LAYOUT.body}>
            {records.map((record) => (
              <tr key={record.public_id} className={LAYOUT.row}>
                <Cell label={columns.manager}>
                  <EmployeeLink employee={record.manager} />
                </Cell>
                <Cell label={columns.type}>
                  {record.relationship_type.code === 'LINE_MANAGER'
                    ? t('emp.reporting.lineManagerType')
                    : record.relationship_type.name}
                </Cell>
                <Cell label={columns.period}>
                  <RecordPeriod from={record.effective_from} to={record.effective_to} />
                </Cell>
                <Cell label={columns.reason}>{record.reason ?? <span className="text-slate-500">—</span>}</Cell>
                {onEnd ? (
                  <Cell label={t('emp.common.actions')}>
                    {record.effective_to === null ? (
                      <RowButton
                        onClick={() => onEnd(record)}
                        label={t('emp.actions.endFor', { name: record.manager.full_name })}
                      >
                        {t('emp.actions.end')}
                      </RowButton>
                    ) : null}
                  </Cell>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
        {records.length === 0 ? (
          <p className="p-6 text-center text-slate-600">{t('emp.reporting.noHistory')}</p>
        ) : null}
      </div>
    </section>
  )
}
