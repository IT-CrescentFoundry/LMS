import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { formatDate } from '../../../lib/format'
import type { Assignment, AssignmentWrite } from '../../../types/employee'
import { Cell, HeaderCell } from '../../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../../admin/tableLayouts'
import { useHasPermission } from '../../auth/authContext'
import { PERMISSIONS } from '../../auth/permissions'
import { CheckboxField, Chip, RowButton } from '../../organisation/OrgParts'
import {
  AddAssignmentDialog,
  ChangeAssignmentDialog,
  CorrectAssignmentDialog,
  EndAssignmentDialog,
} from '../dialogs/AssignmentDialogs'
import { useAssignments } from '../employeeQueries'
import { ActionButton, EmployeeNotice, type EmployeeNoticeValue } from '../EmployeeFormParts'
import { useProfile } from '../profileContext'
import { EmployeeErrorState, RecordPeriod } from '../EmployeeParts'

const LAYOUT = TABLE_LAYOUTS.xl

type AssignmentDialog =
  | { kind: 'add' }
  | { kind: 'change' | 'end' | 'correct'; row: Assignment }
  | null

/**
 * Assignment timeline (`employees.history.view`). History is never overwritten:
 * a transfer or promotion ends one row and starts another.
 */
export function AssignmentsTab() {
  const { t, i18n } = useTranslation()
  const { employee } = useProfile()
  const [includeEnded, setIncludeEnded] = useState(true)
  const query = useAssignments(employee.public_id, includeEnded)
  const canManage = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const [dialog, setDialog] = useState<AssignmentDialog>(null)
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(null)

  function done(message: string, result?: AssignmentWrite) {
    setDialog(null)
    setNotice({ message, warnings: result?.warnings ?? [] })
  }
  const date = (iso: string) => formatDate(iso, i18n.resolvedLanguage)

  const columns = {
    type: t('emp.assignments.columns.type'),
    unit: t('emp.assignments.columns.unit'),
    designation: t('emp.fields.designation'),
    grade: t('emp.fields.grade'),
    level: t('emp.fields.level'),
    location: t('emp.fields.location'),
    period: t('emp.common.period'),
    reason: t('emp.common.reason'),
    ...(canManage ? { actions: t('emp.common.actions') } : {}),
  }
  const dash = <span className="text-slate-500">—</span>

  return (
    <section aria-labelledby="emp-assignments" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="emp-assignments" className="text-lg font-semibold text-slate-900">
          {t('emp.assignments.title')}
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <CheckboxField
            label={t('emp.common.includeEnded')}
            checked={includeEnded}
            onChange={setIncludeEnded}
          />
          {canManage ? (
            <ActionButton onClick={() => setDialog({ kind: 'add' })}>
              <Plus aria-hidden="true" className="size-4" />
              {t('emp.actions.addAssignment')}
            </ActionButton>
          ) : null}
        </div>
      </div>
      <p className="text-sm text-slate-600">{t('emp.assignments.historyNote')}</p>
      {notice ? <EmployeeNotice notice={notice} onDismiss={() => setNotice(null)} /> : null}

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <EmployeeErrorState
          title={t('emp.assignments.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('emp.assignments.title')}</caption>
            <thead className={LAYOUT.head}>
              <tr>
                {Object.values(columns).map((label) => (
                  <HeaderCell key={label}>{label}</HeaderCell>
                ))}
              </tr>
            </thead>
            <tbody className={LAYOUT.body}>
              {query.data.map((row) => (
                <tr key={row.public_id} className={LAYOUT.row}>
                  <Cell label={columns.type} layout="xl">
                    <Chip tone={row.assignment_type === 'primary' ? 'brand' : 'slate'}>
                      {t(`emp.assignmentTypes.${row.assignment_type}`)}
                    </Chip>
                  </Cell>
                  <Cell label={columns.unit} layout="xl">
                    <span className="font-medium text-slate-900">{row.org_unit.name}</span>{' '}
                    <span className="font-mono text-xs text-slate-600">{row.org_unit.code}</span>
                  </Cell>
                  <Cell label={columns.designation} layout="xl">
                    {row.designation?.name ?? dash}
                  </Cell>
                  <Cell label={columns.grade} layout="xl">
                    {row.grade?.name ?? dash}
                  </Cell>
                  <Cell label={columns.level} layout="xl">
                    {row.job_level?.name ?? dash}
                  </Cell>
                  <Cell label={columns.location} layout="xl">
                    {row.location?.name ?? dash}
                  </Cell>
                  <Cell label={columns.period} layout="xl">
                    <RecordPeriod from={row.effective_from} to={row.effective_to} />
                  </Cell>
                  <Cell label={columns.reason} layout="xl">
                    {row.reason ?? dash}
                  </Cell>
                  {canManage ? (
                    <Cell label={t('emp.common.actions')} layout="xl">
                      <div className="flex flex-wrap gap-2">
                        {row.effective_to === null ? (
                          <>
                            <RowButton
                              onClick={() => setDialog({ kind: 'change', row })}
                              label={t('emp.actions.changeFromDateFor', { unit: row.org_unit.name })}
                            >
                              {t('emp.actions.changeFromDate')}
                            </RowButton>
                            <RowButton
                              onClick={() => setDialog({ kind: 'end', row })}
                              label={t('emp.actions.endFor', { name: row.org_unit.name })}
                            >
                              {t('emp.actions.end')}
                            </RowButton>
                          </>
                        ) : null}
                        <RowButton
                          onClick={() => setDialog({ kind: 'correct', row })}
                          label={t('emp.actions.correctFor', { name: row.org_unit.name })}
                        >
                          {t('emp.actions.correct')}
                        </RowButton>
                      </div>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {query.data.length === 0 ? (
            <p className="p-6 text-center text-slate-600">{t('emp.assignments.empty')}</p>
          ) : null}
        </div>
      )}

      {dialog?.kind === 'add' ? (
        <AddAssignmentDialog
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(result) =>
            done(t('emp.messages.assignmentAdded', { unit: result.assignment.org_unit.name }), result)
          }
        />
      ) : null}
      {dialog?.kind === 'change' ? (
        <ChangeAssignmentDialog
          employee={employee}
          row={dialog.row}
          onClose={() => setDialog(null)}
          onDone={(result, effectiveDate) =>
            done(t('emp.messages.assignmentChanged', { date: date(effectiveDate) }), result)
          }
        />
      ) : null}
      {dialog?.kind === 'end' ? (
        <EndAssignmentDialog
          employee={employee}
          row={dialog.row}
          onClose={() => setDialog(null)}
          onDone={(lastDay) =>
            done(t('emp.messages.assignmentEnded', { unit: dialog.row.org_unit.name, date: date(lastDay) }))
          }
        />
      ) : null}
      {dialog?.kind === 'correct' ? (
        <CorrectAssignmentDialog
          employee={employee}
          row={dialog.row}
          onClose={() => setDialog(null)}
          onDone={(result) => done(t('emp.messages.assignmentCorrected'), result)}
        />
      ) : null}
    </section>
  )
}
