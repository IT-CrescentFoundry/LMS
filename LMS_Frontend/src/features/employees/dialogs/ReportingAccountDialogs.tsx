import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { AccountStatusBadge, RoleChips } from '../../../components/Badges'
import { inputClassName, labelClassName, secondaryButtonClassName } from '../../../components/formStyles'
import { Modal } from '../../../components/Modal'
import { formatDate } from '../../../lib/format'
import { employeeService } from '../../../services/employeeService'
import type { AccountRef, Employee, EmployeeAccount, ReportingRecord } from '../../../types/employee'
import { useAuth } from '../../auth/authContext'
import { DialogActions, InfoNote, TextAreaField, TextField } from '../../organisation/OrgParts'
import { useServerFieldErrors } from '../employeeErrorMessage'
import { useEmployeeMutation, useUnlinkedAccounts } from '../employeeQueries'
import { EmployeeChangeError, EmployeeSelect } from '../EmployeeFormParts'
import { blankToNull } from '../formValues'
import { EndRecordDialog } from './EndRecordDialog'

// ---------------------------------------------------------------- reporting

/**
 * Sets the line manager from a date. A current line manager is replaced from
 * that date (their line ends the day before); the relationship type is the
 * server default (LINE_MANAGER). Being a manager grants no access rights.
 */
export function SetManagerDialog({
  employee,
  current,
  onClose,
  onDone,
}: {
  employee: Employee
  current: ReportingRecord | null
  onClose: () => void
  onDone: (record: ReportingRecord) => void
}) {
  const { t, i18n } = useTranslation()
  const [managerId, setManagerId] = useState('')
  const [from, setFrom] = useState('')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const mutation = useEmployeeMutation(() =>
    employeeService.setManager(employee.public_id, {
      manager_id: managerId,
      effective_from: from,
      reason: blankToNull(reason),
    }),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const required = t('org.errors.required')
  const errors = { manager: managerId === '' ? required : undefined, from: from === '' ? required : undefined }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.manager || errors.from) return
    mutation.mutate(undefined, { onSuccess: onDone })
  }

  return (
    <Modal
      title={
        current
          ? t('emp.dialogs.changeManagerTitle', { name: employee.full_name })
          : t('emp.dialogs.setManagerTitle', { name: employee.full_name })
      }
      description={t('emp.dialogs.setManagerHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <InfoNote>{t('emp.reporting.note')}</InfoNote>
        {current ? (
          <p className="text-sm text-slate-800">
            {t('emp.dialogs.currentManager', {
              manager: `${current.manager.employee_code} · ${current.manager.full_name}`,
              from: current.effective_from
                ? formatDate(current.effective_from, i18n.resolvedLanguage)
                : t('emp.common.startNotRecorded'),
            })}
          </p>
        ) : null}
        <EmployeeSelect
          label={t('emp.fields.manager')}
          value={managerId}
          onChange={setManagerId}
          excludeId={employee.public_id}
          required
          error={(showErrors ? errors.manager : undefined) ?? serverError('manager_id')}
        />
        <TextField
          label={t('emp.fields.effectiveFrom')}
          type="date"
          value={from}
          onChange={setFrom}
          required
          hint={current ? t('emp.hints.replacesManager') : t('emp.hints.effectiveFrom')}
          error={(showErrors ? errors.from : undefined) ?? serverError('effective_from')}
        />
        <TextAreaField label={t('emp.common.reason')} value={reason} onChange={setReason} maxLength={500} />
        {mutation.isError ? <EmployeeChangeError error={mutation.error} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.saveManager')} />
      </form>
    </Modal>
  )
}

export function EndReportingDialog({
  employee,
  record,
  onClose,
  onDone,
}: {
  employee: Employee
  record: ReportingRecord
  onClose: () => void
  onDone: (lastDay: string) => void
}) {
  const { t } = useTranslation()
  return (
    <EndRecordDialog
      title={t('emp.dialogs.endReportingTitle', { manager: record.manager.full_name })}
      description={t('emp.dialogs.endReportingHint')}
      startedOn={record.effective_from}
      submitLabel={t('emp.actions.confirmEnd')}
      onSubmit={(body) => employeeService.endReporting(employee.public_id, record.public_id, body)}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

// ------------------------------------------------------------------ account

/**
 * Links an unlinked login account (server search, `linked=false`). The acting
 * user's own account is shown but cannot be chosen. Nothing about the account
 * itself changes; privilege rules are checked by the server.
 */
export function LinkAccountDialog({
  employee,
  onClose,
  onDone,
}: {
  employee: Employee
  onClose: () => void
  onDone: (result: EmployeeAccount, loginId: string) => void
}) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const groupName = useId()
  const searchId = useId()
  const [search, setSearch] = useState('')
  const [applied, setApplied] = useState('')
  const [accountId, setAccountId] = useState('')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const accounts = useUnlinkedAccounts(applied, true)
  const items = accounts.data?.items ?? []
  const chosen = items.find((item) => item.public_id === accountId)
  const mutation = useEmployeeMutation(
    () => employeeService.linkAccount(employee.public_id, { user_public_id: accountId, reason: blankToNull(reason) }),
    { alsoInvalidateUsers: true },
  )
  const accountError = accountId === '' ? t('emp.validation.chooseAccount') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (accountError) return
    mutation.mutate(undefined, { onSuccess: (result) => onDone(result, chosen?.login_id ?? '') })
  }

  return (
    <Modal
      title={t('emp.dialogs.linkAccountTitle', { name: employee.full_name })}
      description={t('emp.dialogs.linkAccountHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {/* Its own search: Enter searches and never submits the link form. */}
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-0 flex-1 space-y-1.5">
            <label htmlFor={searchId} className={labelClassName}>
              {t('emp.fields.accountSearch')}
            </label>
            <input
              id={searchId}
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  setApplied(search.trim())
                }
              }}
              maxLength={100}
              placeholder={t('admin.users.searchPlaceholder')}
              autoComplete="off"
              data-autofocus
              className={inputClassName()}
            />
          </div>
          <button type="button" onClick={() => setApplied(search.trim())} className={secondaryButtonClassName}>
            {t('emp.actions.search')}
          </button>
        </div>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t('emp.account.unlinkedAccounts')}</legend>
          {accounts.isPending ? (
            <p className="text-sm text-slate-600">{t('emp.account.searching')}</p>
          ) : accounts.isError ? (
            <EmployeeChangeError error={accounts.error} />
          ) : items.length === 0 ? (
            <p className="text-sm text-slate-600">{t('emp.account.noUnlinked')}</p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {items.map((item) => {
                const own = item.public_id === user?.public_id
                const id = `${groupName}-${item.public_id}`
                return (
                  <li key={item.public_id} className="flex gap-3 p-3">
                    <input
                      id={id}
                      type="radio"
                      name={groupName}
                      value={item.public_id}
                      checked={accountId === item.public_id}
                      disabled={own}
                      onChange={() => setAccountId(item.public_id)}
                      aria-describedby={own ? `${id}-own` : undefined}
                      className="mt-1 size-4 shrink-0 border-slate-300 text-brand-700 focus:ring-2 focus:ring-brand-500"
                    />
                    <div className="min-w-0 flex-1 space-y-1">
                      <label htmlFor={id} className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-mono font-medium text-slate-900">{item.login_id}</span>
                        <span className="text-slate-700">{item.display_name}</span>
                        <AccountStatusBadge status={item.status} />
                      </label>
                      <RoleChips roles={item.roles} />
                      {own ? (
                        <p id={`${id}-own`} className="text-xs font-medium text-slate-600">
                          {t('emp.account.ownAccount')}
                        </p>
                      ) : null}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
          {showErrors && accountError ? <p className="text-sm text-red-700">{accountError}</p> : null}
        </fieldset>
        <TextAreaField label={t('emp.common.reason')} value={reason} onChange={setReason} maxLength={500} />
        {mutation.isError ? <EmployeeChangeError error={mutation.error} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.linkAccount')} />
      </form>
    </Modal>
  )
}

/** Unlinks an account after an explicit confirmation; the account itself is unchanged. */
export function UnlinkAccountDialog({
  employee,
  account,
  onClose,
  onDone,
}: {
  employee: Employee
  account: AccountRef
  onClose: () => void
  onDone: (result: EmployeeAccount) => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  const [step, setStep] = useState<'form' | 'confirm'>('form')
  const mutation = useEmployeeMutation(
    () =>
      employeeService.unlinkAccount(employee.public_id, {
        user_public_id: account.public_id,
        reason: blankToNull(reason),
      }),
    { alsoInvalidateUsers: true },
  )

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'form') {
      setStep('confirm')
      return
    }
    mutation.mutate(undefined, { onSuccess: onDone })
  }

  return (
    <Modal
      title={t('emp.dialogs.unlinkAccountTitle', { login: account.login_id })}
      description={t('emp.dialogs.unlinkAccountHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {step === 'form' ? (
          <TextAreaField label={t('emp.common.reason')} value={reason} onChange={setReason} maxLength={500} />
        ) : (
          <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-950">
            <p className="font-medium">
              {t('emp.dialogs.unlinkConfirm', { login: account.login_id, name: employee.full_name })}
            </p>
            <p>{t('emp.dialogs.unlinkKeepsAccount')}</p>
          </div>
        )}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} /> : null}
        <DialogActions
          onCancel={step === 'confirm' && !mutation.isPending ? () => setStep('form') : onClose}
          cancelLabel={step === 'confirm' ? t('org.actions.back') : undefined}
          busy={mutation.isPending}
          tone="danger"
          submitLabel={step === 'form' ? t('org.actions.continue') : t('emp.actions.confirmUnlink')}
        />
      </form>
    </Modal>
  )
}
