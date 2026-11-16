import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { formatDate } from '../../../lib/format'
import type { EffectiveRole, RoleRecord } from '../../../types/employee'
import type { Ref } from '../../../types/organisation'
import { Cell, HeaderCell } from '../../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../../admin/tableLayouts'
import { useHasPermission } from '../../auth/authContext'
import { PERMISSIONS } from '../../auth/permissions'
import { CheckboxField, Chip, InfoNote, RowButton } from '../../organisation/OrgParts'
import { EndRoleDialog, RoleDialog } from '../dialogs/RoleResponsibilityDialogs'
import { useFunctionalRoles } from '../employeeQueries'
import { ActionButton, EmployeeNotice, type EmployeeNoticeValue } from '../EmployeeFormParts'
import { useProfile } from '../profileContext'
import { EmployeeErrorState, RecordPeriod } from '../EmployeeParts'

const LAYOUT = TABLE_LAYOUTS.md

type RoleDialogState =
  | { kind: 'manual' }
  | { kind: 'exclusion'; role: Ref }
  | { kind: 'end'; record: RoleRecord }
  | null

/**
 * Functional roles on the selected date: derived from every assignment (through
 * designation mappings) plus manual roles, minus exclusions - all computed by the
 * server. Excluded roles are listed but marked "not in effect".
 */
export function FunctionalRolesTab() {
  const { t, i18n } = useTranslation()
  const { employee, asOf } = useProfile()
  const [includeEnded, setIncludeEnded] = useState(false)
  const query = useFunctionalRoles(employee.public_id, asOf, includeEnded)
  const canManage = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const [dialog, setDialog] = useState<RoleDialogState>(null)
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(null)

  function done(message: string) {
    setDialog(null)
    setNotice({ message, warnings: [] })
  }

  const columns = {
    role: t('emp.roles.columns.role'),
    effect: t('emp.roles.columns.effect'),
    sources: t('emp.roles.columns.sources'),
    ...(canManage ? { actions: t('emp.common.actions') } : {}),
  }
  const recordColumns = {
    kind: t('emp.roles.columns.kind'),
    role: t('emp.roles.columns.role'),
    period: t('emp.common.period'),
    reason: t('emp.common.reason'),
    ...(canManage ? { actions: t('emp.common.actions') } : {}),
  }

  if (query.isPending) return <LoadingState />
  if (query.isError) {
    return (
      <EmployeeErrorState
        title={t('emp.roles.loadError')}
        error={query.error}
        onRetry={() => void query.refetch()}
        isRetrying={query.isFetching}
      />
    )
  }
  const data = query.data

  return (
    <div className="space-y-6">
      <InfoNote>{t('emp.roles.note')}</InfoNote>
      {notice ? <EmployeeNotice notice={notice} onDismiss={() => setNotice(null)} /> : null}
      <section aria-labelledby="emp-roles" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="emp-roles" className="text-lg font-semibold text-slate-900">
            {t('emp.roles.title', { date: formatDate(data.as_of, i18n.resolvedLanguage) })}
          </h2>
          {canManage ? (
            <ActionButton onClick={() => setDialog({ kind: 'manual' })}>
              <Plus aria-hidden="true" className="size-4" />
              {t('emp.actions.assignRole')}
            </ActionButton>
          ) : null}
        </div>
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('emp.roles.caption')}</caption>
            <thead className={LAYOUT.head}>
              <tr>
                {Object.values(columns).map((label) => (
                  <HeaderCell key={label}>{label}</HeaderCell>
                ))}
              </tr>
            </thead>
            <tbody className={LAYOUT.body}>
              {data.roles.map((role) => (
                <tr key={role.functional_role.public_id} className={LAYOUT.row}>
                  <Cell label={columns.role}>
                    <span className="font-medium text-slate-900">{role.functional_role.name}</span>{' '}
                    <span className="font-mono text-xs text-slate-600">{role.functional_role.code}</span>
                  </Cell>
                  <Cell label={columns.effect}>
                    {role.effective ? (
                      <Chip tone="brand">{t('emp.roles.inEffect')}</Chip>
                    ) : (
                      <Chip tone="slate">{t('emp.roles.notInEffect')}</Chip>
                    )}
                  </Cell>
                  <Cell label={columns.sources}>
                    <RoleSources role={role} />
                  </Cell>
                  {canManage ? (
                    <Cell label={t('emp.common.actions')}>
                      {role.derived_from.length > 0 && role.exclusion === null ? (
                        <RowButton
                          onClick={() => setDialog({ kind: 'exclusion', role: role.functional_role })}
                          label={t('emp.actions.excludeFor', { role: role.functional_role.name })}
                        >
                          {t('emp.actions.exclude')}
                        </RowButton>
                      ) : null}
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {data.roles.length === 0 ? (
            <p className="p-6 text-center text-slate-600">{t('emp.roles.empty')}</p>
          ) : null}
        </div>
      </section>

      <section aria-labelledby="emp-role-records" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="emp-role-records" className="text-lg font-semibold text-slate-900">
            {t('emp.roles.recordsTitle')}
          </h2>
          <CheckboxField label={t('emp.common.includeEnded')} checked={includeEnded} onChange={setIncludeEnded} />
        </div>
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('emp.roles.recordsTitle')}</caption>
            <thead className={LAYOUT.head}>
              <tr>
                {Object.values(recordColumns).map((label) => (
                  <HeaderCell key={label}>{label}</HeaderCell>
                ))}
              </tr>
            </thead>
            <tbody className={LAYOUT.body}>
              {data.records.map((record) => (
                <tr key={record.public_id} className={LAYOUT.row}>
                  <Cell label={recordColumns.kind}>
                    <Chip tone={record.kind === 'exclusion' ? 'ember' : 'brand'}>
                      {t(`emp.roles.kinds.${record.kind}`)}
                    </Chip>
                  </Cell>
                  <Cell label={recordColumns.role}>
                    {record.functional_role.name}{' '}
                    <span className="font-mono text-xs text-slate-600">{record.functional_role.code}</span>
                  </Cell>
                  <Cell label={recordColumns.period}>
                    <RecordPeriod from={record.effective_from} to={record.effective_to} />
                  </Cell>
                  <Cell label={recordColumns.reason}>
                    {record.reason ?? <span className="text-slate-500">—</span>}
                  </Cell>
                  {canManage ? (
                    <Cell label={t('emp.common.actions')}>
                      {record.effective_to === null ? (
                        <RowButton
                          onClick={() => setDialog({ kind: 'end', record })}
                          label={t('emp.actions.endFor', { name: record.functional_role.name })}
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
          {data.records.length === 0 ? (
            <p className="p-6 text-center text-slate-600">{t('emp.roles.noRecords')}</p>
          ) : null}
        </div>
      </section>

      {dialog?.kind === 'manual' || dialog?.kind === 'exclusion' ? (
        <RoleDialog
          employee={employee}
          kind={dialog.kind}
          role={dialog.kind === 'exclusion' ? dialog.role : undefined}
          onClose={() => setDialog(null)}
          onDone={(record) =>
            done(
              record.kind === 'manual'
                ? t('emp.messages.roleAssigned', { role: record.functional_role.name })
                : t('emp.messages.roleExcluded', { role: record.functional_role.name }),
            )
          }
        />
      ) : null}
      {dialog?.kind === 'end' ? (
        <EndRoleDialog
          employee={employee}
          record={dialog.record}
          onClose={() => setDialog(null)}
          onDone={(lastDay) =>
            done(
              t('emp.messages.recordEnded', {
                name: dialog.record.functional_role.name,
                date: formatDate(lastDay, i18n.resolvedLanguage),
              }),
            )
          }
        />
      ) : null}
    </div>
  )
}

function RoleSources({ role }: { role: EffectiveRole }) {
  const { t } = useTranslation()
  return (
    <ul className="space-y-1">
      {role.derived_from.map((source) => (
        <li key={`${source.assignment}-${source.mapping}`} className="text-slate-800">
          {t('emp.roles.derived', {
            designation: source.designation.name,
            unit: source.org_unit.name,
            type: t(`emp.assignmentTypes.${source.assignment_type}`),
          })}
        </li>
      ))}
      {role.manual ? <li className="text-slate-800">{t('emp.roles.manual')}</li> : null}
      {role.exclusion ? (
        <li className="font-medium text-orange-900">
          {t('emp.roles.excluded')}
          {role.exclusion.reason ? ` — ${role.exclusion.reason}` : ''}
        </li>
      ) : null}
    </ul>
  )
}
