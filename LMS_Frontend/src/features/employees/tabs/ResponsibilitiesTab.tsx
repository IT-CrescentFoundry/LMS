import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { formatDate } from '../../../lib/format'
import type { ResponsibilityRecord } from '../../../types/employee'
import { Cell, HeaderCell } from '../../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../../admin/tableLayouts'
import { useHasPermission } from '../../auth/authContext'
import { PERMISSIONS } from '../../auth/permissions'
import { CheckboxField, InfoNote, RowButton } from '../../organisation/OrgParts'
import { EndResponsibilityDialog, ResponsibilityDialog } from '../dialogs/RoleResponsibilityDialogs'
import { useResponsibilities } from '../employeeQueries'
import { ActionButton, EmployeeNotice, type EmployeeNoticeValue } from '../EmployeeFormParts'
import { useProfile } from '../profileContext'
import { EmployeeErrorState, RecordPeriod } from '../EmployeeParts'

const LAYOUT = TABLE_LAYOUTS.md

/** Responsibilities (duties such as fire warden), optionally for a unit or location. */
export function ResponsibilitiesTab() {
  const { t, i18n } = useTranslation()
  const { employee } = useProfile()
  const [includeEnded, setIncludeEnded] = useState(false)
  const query = useResponsibilities(employee.public_id, includeEnded)
  const canManage = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const [dialog, setDialog] = useState<{ kind: 'add' } | { kind: 'end'; record: ResponsibilityRecord } | null>(null)
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(null)

  function done(message: string) {
    setDialog(null)
    setNotice({ message, warnings: [] })
  }

  const columns = {
    responsibility: t('emp.responsibilities.columns.responsibility'),
    context: t('emp.responsibilities.columns.context'),
    period: t('emp.common.period'),
    reason: t('emp.common.reason'),
    ...(canManage ? { actions: t('emp.common.actions') } : {}),
  }

  return (
    <section aria-labelledby="emp-responsibilities" className="space-y-4">
      <InfoNote>{t('emp.responsibilities.note')}</InfoNote>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="emp-responsibilities" className="text-lg font-semibold text-slate-900">
          {t('emp.responsibilities.title')}
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <CheckboxField label={t('emp.common.includeEnded')} checked={includeEnded} onChange={setIncludeEnded} />
          {canManage ? (
            <ActionButton onClick={() => setDialog({ kind: 'add' })}>
              <Plus aria-hidden="true" className="size-4" />
              {t('emp.actions.addResponsibility')}
            </ActionButton>
          ) : null}
        </div>
      </div>
      {notice ? <EmployeeNotice notice={notice} onDismiss={() => setNotice(null)} /> : null}
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <EmployeeErrorState
          title={t('emp.responsibilities.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('emp.responsibilities.title')}</caption>
            <thead className={LAYOUT.head}>
              <tr>
                {Object.values(columns).map((label) => (
                  <HeaderCell key={label}>{label}</HeaderCell>
                ))}
              </tr>
            </thead>
            <tbody className={LAYOUT.body}>
              {query.data.map((record) => (
                <tr key={record.public_id} className={LAYOUT.row}>
                  <Cell label={columns.responsibility}>
                    <span className="font-medium text-slate-900">{record.responsibility.name}</span>{' '}
                    <span className="font-mono text-xs text-slate-600">{record.responsibility.code}</span>
                  </Cell>
                  <Cell label={columns.context}>
                    {record.context_unit || record.context_location ? (
                      <span className="space-y-0.5">
                        {record.context_unit ? (
                          <span className="block">
                            {t('emp.responsibilities.inUnit', { unit: record.context_unit.name })}
                          </span>
                        ) : null}
                        {record.context_location ? (
                          <span className="block">
                            {t('emp.responsibilities.atLocation', { location: record.context_location.name })}
                          </span>
                        ) : null}
                      </span>
                    ) : (
                      <span className="text-slate-600">{t('emp.responsibilities.noContext')}</span>
                    )}
                  </Cell>
                  <Cell label={columns.period}>
                    <RecordPeriod from={record.effective_from} to={record.effective_to} />
                  </Cell>
                  <Cell label={columns.reason}>{record.reason ?? <span className="text-slate-500">—</span>}</Cell>
                  {canManage ? (
                    <Cell label={t('emp.common.actions')}>
                      {record.effective_to === null ? (
                        <RowButton
                          onClick={() => setDialog({ kind: 'end', record })}
                          label={t('emp.actions.endFor', { name: record.responsibility.name })}
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
          {query.data.length === 0 ? (
            <p className="p-6 text-center text-slate-600">{t('emp.responsibilities.empty')}</p>
          ) : null}
        </div>
      )}

      {dialog?.kind === 'add' ? (
        <ResponsibilityDialog
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(record) => done(t('emp.messages.responsibilityAdded', { name: record.responsibility.name }))}
        />
      ) : null}
      {dialog?.kind === 'end' ? (
        <EndResponsibilityDialog
          employee={employee}
          record={dialog.record}
          onClose={() => setDialog(null)}
          onDone={(lastDay) =>
            done(
              t('emp.messages.recordEnded', {
                name: dialog.record.responsibility.name,
                date: formatDate(lastDay, i18n.resolvedLanguage),
              }),
            )
          }
        />
      ) : null}
    </section>
  )
}
