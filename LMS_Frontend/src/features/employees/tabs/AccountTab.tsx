import { Link2, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AccountStatusBadge } from '../../../components/Badges'
import { LoadingState } from '../../../components/LoadingState'
import { ACCOUNT_FLAGS, type AccountFlag, type AccountRef } from '../../../types/employee'
import { Cell, HeaderCell } from '../../admin/AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../../admin/tableLayouts'
import { useHasPermission } from '../../auth/authContext'
import { PERMISSIONS } from '../../auth/permissions'
import { InfoNote, RowButton } from '../../organisation/OrgParts'
import { LinkAccountDialog, UnlinkAccountDialog } from '../dialogs/ReportingAccountDialogs'
import { useEmployeeAccount } from '../employeeQueries'
import { ActionButton, EmployeeNotice, type EmployeeNoticeValue } from '../EmployeeFormParts'
import { useProfile } from '../profileContext'
import { EmployeeErrorState } from '../EmployeeParts'
import { EventLine } from './HistoryTab'

const LAYOUT = TABLE_LAYOUTS.md

function isAccountFlag(value: string): value is AccountFlag {
  return (ACCOUNT_FLAGS as readonly string[]).includes(value)
}

/**
 * Linked login accounts. Accounts are never linked, unlinked or suspended
 * automatically; mismatches are only flagged. Linking and unlinking need BOTH
 * `employees.manage` and `user_accounts.manage` (the API checks them too); the
 * account picker additionally needs `user_accounts.view`.
 */
export function AccountTab() {
  const { t } = useTranslation()
  const { employee } = useProfile()
  const query = useEmployeeAccount(employee.public_id)
  const canManageEmployees = useHasPermission(PERMISSIONS.EMPLOYEES_MANAGE)
  const canManageAccounts = useHasPermission(PERMISSIONS.USER_ACCOUNTS_MANAGE)
  const canViewAccounts = useHasPermission(PERMISSIONS.USER_ACCOUNTS_VIEW)
  const canUnlink = canManageEmployees && canManageAccounts
  const canLink = canUnlink && canViewAccounts
  const [dialog, setDialog] = useState<{ kind: 'link' } | { kind: 'unlink'; account: AccountRef } | null>(null)
  const [notice, setNotice] = useState<EmployeeNoticeValue | null>(null)

  function done(message: string) {
    setDialog(null)
    setNotice({ message, warnings: [] })
  }

  if (query.isPending) return <LoadingState />
  if (query.isError) {
    return (
      <EmployeeErrorState
        title={t('emp.account.loadError')}
        error={query.error}
        onRetry={() => void query.refetch()}
        isRetrying={query.isFetching}
      />
    )
  }
  const data = query.data
  const columns = {
    login: t('emp.account.columns.login'),
    name: t('emp.account.columns.name'),
    status: t('emp.account.columns.status'),
    ...(canUnlink ? { actions: t('emp.common.actions') } : {}),
  }

  return (
    <div className="space-y-6">
      <InfoNote>{t('emp.account.note')}</InfoNote>
      {notice ? <EmployeeNotice notice={notice} onDismiss={() => setNotice(null)} /> : null}

      {data.flags.length > 0 ? (
        <div role="status" className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-amber-700" />
          <div className="min-w-0 space-y-1">
            <p className="font-medium">{t('emp.account.flagsTitle')}</p>
            <ul className="list-disc space-y-0.5 pl-5">
              {data.flags.map((flag) => (
                <li key={flag}>{isAccountFlag(flag) ? t(`emp.account.flags.${flag}`) : flag}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <section aria-labelledby="emp-linked-accounts" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="emp-linked-accounts" className="text-lg font-semibold text-slate-900">
            {t('emp.account.linked')}
          </h2>
          {canLink ? (
            <ActionButton onClick={() => setDialog({ kind: 'link' })}>
              <Link2 aria-hidden="true" className="size-4" />
              {t('emp.actions.linkAccount')}
            </ActionButton>
          ) : null}
        </div>
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('emp.account.linked')}</caption>
            <thead className={LAYOUT.head}>
              <tr>
                {Object.values(columns).map((label) => (
                  <HeaderCell key={label}>{label}</HeaderCell>
                ))}
              </tr>
            </thead>
            <tbody className={LAYOUT.body}>
              {data.accounts.map((account) => (
                <tr key={account.public_id} className={LAYOUT.row}>
                  <Cell label={columns.login}>
                    <span className="font-mono text-slate-900">{account.login_id}</span>
                  </Cell>
                  <Cell label={columns.name}>{account.display_name}</Cell>
                  <Cell label={columns.status}>
                    <AccountStatusBadge status={account.status} />
                  </Cell>
                  {canUnlink ? (
                    <Cell label={t('emp.common.actions')}>
                      <RowButton
                        onClick={() => setDialog({ kind: 'unlink', account })}
                        label={t('emp.actions.unlinkFor', { login: account.login_id })}
                      >
                        {t('emp.actions.unlink')}
                      </RowButton>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {data.accounts.length === 0 ? (
            <p className="p-6 text-center text-slate-600">{t('emp.account.none')}</p>
          ) : null}
        </div>
        {data.accounts.some((account) => account.status === 'disabled') ? (
          <p className="text-xs text-slate-600">{t('emp.account.disabledNote')}</p>
        ) : null}
      </section>

      <section aria-labelledby="emp-link-history" className="space-y-3">
        <h2 id="emp-link-history" className="text-lg font-semibold text-slate-900">
          {t('emp.account.history')}
        </h2>
        {data.history.length === 0 ? (
          <p className="text-sm text-slate-600">{t('emp.account.noHistory')}</p>
        ) : (
          <ol className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-sm">
            {data.history.map((event) => (
              <li key={event.event_id} className="p-4">
                <EventLine event={event} />
              </li>
            ))}
          </ol>
        )}
      </section>

      {dialog?.kind === 'link' ? (
        <LinkAccountDialog
          employee={employee}
          onClose={() => setDialog(null)}
          onDone={(_result, loginId) => done(t('emp.messages.accountLinked', { login: loginId }))}
        />
      ) : null}
      {dialog?.kind === 'unlink' ? (
        <UnlinkAccountDialog
          employee={employee}
          account={dialog.account}
          onClose={() => setDialog(null)}
          onDone={() => done(t('emp.messages.accountUnlinked', { login: dialog.account.login_id }))}
        />
      ) : null}
    </div>
  )
}
