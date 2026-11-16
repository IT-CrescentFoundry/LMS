import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Modal } from '../../../components/Modal'
import { SUPPORTED_LANGUAGES } from '../../../i18n/languages'
import { employeeService } from '../../../services/employeeService'
import {
  EMPLOYEE_LANGUAGES,
  type Employee,
  type EmployeeCorrectionBody,
  type EmployeeCreateBody,
  type EmployeeLanguage,
  type EmploymentStatus,
} from '../../../types/employee'
import { DialogActions, SelectField, TextAreaField, TextField } from '../../organisation/OrgParts'
import { useServerFieldErrors } from '../employeeErrorMessage'
import { useEmployeeMutation, useReloadEmployeesAndClose } from '../employeeQueries'
import { EmployeeChangeError } from '../EmployeeFormParts'
import { blankToNull, isValidEmployeeCode, isValidWorkEmail, normaliseEmployeeCode } from '../formValues'

function isLanguage(value: string): value is EmployeeLanguage {
  return (EMPLOYEE_LANGUAGES as readonly string[]).includes(value)
}

function useLanguageOptions() {
  return EMPLOYEE_LANGUAGES.map((code) => ({
    value: code,
    label: SUPPORTED_LANGUAGES.find((item) => item.code === code)?.nativeName ?? code,
  }))
}

// ------------------------------------------------------------ create / edit

/**
 * Create an employee record, or correct one's recorded details (changed fields
 * only, with the version last read). The employment status is not edited here:
 * status changes and separation have their own audited workflows.
 */
export function EmployeeFormDialog({
  mode,
  employee,
  onClose,
  onDone,
}: {
  mode: 'create' | 'edit'
  employee?: Employee
  onClose: () => void
  onDone: (employee: Employee) => void
}) {
  const { t } = useTranslation()
  const languageOptions = useLanguageOptions()
  const [code, setCode] = useState(employee?.employee_code ?? '')
  const [fullName, setFullName] = useState(employee?.full_name ?? '')
  const [displayName, setDisplayName] = useState(employee?.display_name ?? '')
  const [language, setLanguage] = useState<string>(employee?.preferred_language ?? '')
  const [email, setEmail] = useState(employee?.work_email ?? '')
  const [status, setStatus] = useState<EmploymentStatus | ''>('')
  const [joining, setJoining] = useState(employee?.date_of_joining ?? '')
  const [lastWorkingDay, setLastWorkingDay] = useState('')
  const [externalRef, setExternalRef] = useState(employee?.external_ref ?? '')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const [nothingChanged, setNothingChanged] = useState(false)
  const reload = useReloadEmployeesAndClose(onClose)
  const mutation = useEmployeeMutation(
    (change: { create: EmployeeCreateBody } | { correct: EmployeeCorrectionBody }): Promise<Employee> =>
      'create' in change
        ? employeeService.create(change.create)
        : employeeService.correct(employee?.public_id ?? '', change.correct),
  )
  const serverError = useServerFieldErrors(mutation.error)

  const required = t('org.errors.required')
  const errors = {
    code: code.trim() === '' ? required : !isValidEmployeeCode(code) ? t('emp.validation.employeeCode') : undefined,
    fullName: fullName.trim() === '' ? required : undefined,
    email: email.trim() !== '' && !isValidWorkEmail(email) ? t('emp.validation.workEmail') : undefined,
    lastWorkingDay: mode === 'create' && status === 'separated' && lastWorkingDay === '' ? required : undefined,
    order:
      mode === 'create' && status === 'separated' && joining !== '' && lastWorkingDay !== '' && lastWorkingDay < joining
        ? t('emp.validation.separationBeforeJoining')
        : undefined,
  }
  const hasErrors = Object.values(errors).some(Boolean)
  const normalised = normaliseEmployeeCode(code)

  function buildCorrection(current: Employee): EmployeeCorrectionBody | null {
    const body: Omit<EmployeeCorrectionBody, 'version' | 'reason'> = {}
    if (normalised !== current.employee_code) body.employee_code = normalised
    if (fullName.trim() !== current.full_name) body.full_name = fullName.trim()
    if (blankToNull(displayName) !== current.display_name) body.display_name = blankToNull(displayName)
    const nextLanguage = isLanguage(language) ? language : null
    if (nextLanguage !== current.preferred_language) body.preferred_language = nextLanguage
    if (blankToNull(email) !== current.work_email) body.work_email = blankToNull(email)
    if ((joining || null) !== current.date_of_joining) body.date_of_joining = joining || null
    if (blankToNull(externalRef) !== current.external_ref) body.external_ref = blankToNull(externalRef)
    if (Object.keys(body).length === 0) return null
    return { version: current.version, reason: blankToNull(reason), ...body }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (hasErrors) return
    if (mode === 'edit' && employee) {
      const correction = buildCorrection(employee)
      if (correction === null) {
        setNothingChanged(true)
        return
      }
      setNothingChanged(false)
      mutation.mutate({ correct: correction }, { onSuccess: onDone })
      return
    }
    mutation.mutate(
      {
        create: {
          employee_code: normalised,
          full_name: fullName.trim(),
          display_name: blankToNull(displayName),
          preferred_language: isLanguage(language) ? language : null,
          work_email: blankToNull(email),
          employment_status: status === '' ? null : status,
          date_of_joining: joining || null,
          // Recorded only for an employee who had already left when created.
          date_of_separation: status === 'separated' ? lastWorkingDay : null,
          external_ref: blankToNull(externalRef),
        },
      },
      { onSuccess: onDone },
    )
  }

  return (
    <Modal
      title={mode === 'create' ? t('emp.dialogs.createTitle') : t('emp.dialogs.editTitle', { name: employee?.full_name })}
      description={mode === 'edit' ? t('emp.dialogs.editHint') : t('emp.dialogs.createHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('emp.fields.employeeCode')}
            value={code}
            onChange={setCode}
            required
            maxLength={30}
            hint={
              normalised !== '' && normalised !== code
                ? t('emp.hints.employeeCodeStored', { code: normalised })
                : t('emp.hints.employeeCode')
            }
            error={(showErrors ? errors.code : undefined) ?? serverError('employee_code')}
            autoFocus
          />
          <TextField
            label={t('emp.fields.fullName')}
            value={fullName}
            onChange={setFullName}
            required
            maxLength={200}
            error={(showErrors ? errors.fullName : undefined) ?? serverError('full_name')}
          />
          <TextField
            label={t('emp.fields.displayName')}
            value={displayName}
            onChange={setDisplayName}
            maxLength={200}
            error={serverError('display_name')}
          />
          <SelectField
            label={t('emp.fields.preferredLanguage')}
            value={language}
            onChange={setLanguage}
            options={languageOptions}
            emptyLabel={t('emp.common.notRecorded')}
            error={serverError('preferred_language')}
          />
          <TextField
            label={t('emp.fields.workEmail')}
            value={email}
            onChange={setEmail}
            maxLength={254}
            hint={t('emp.hints.workEmail')}
            error={(showErrors ? errors.email : undefined) ?? serverError('work_email')}
          />
          <TextField
            label={t('emp.fields.dateOfJoining')}
            type="date"
            value={joining}
            onChange={setJoining}
            error={serverError('date_of_joining')}
          />
          {mode === 'create' ? (
            <SelectField
              label={t('emp.fields.status')}
              value={status}
              onChange={(value) => setStatus(value as EmploymentStatus | '')}
              options={[
                { value: 'active', label: t('emp.status.active') },
                { value: 'on_leave', label: t('emp.status.on_leave') },
                { value: 'separated', label: t('emp.status.separated') },
              ]}
              emptyLabel={t('emp.status.unknown')}
              hint={t('emp.hints.statusOnCreate')}
              error={serverError('employment_status')}
            />
          ) : null}
          {mode === 'create' && status === 'separated' ? (
            <TextField
              label={t('emp.fields.lastWorkingDay')}
              type="date"
              value={lastWorkingDay}
              onChange={setLastWorkingDay}
              required
              hint={t('emp.hints.separatedOnCreate')}
              error={(showErrors ? (errors.lastWorkingDay ?? errors.order) : undefined) ?? serverError('date_of_separation')}
            />
          ) : null}
          <TextField
            label={t('emp.fields.externalRef')}
            value={externalRef}
            onChange={setExternalRef}
            maxLength={100}
            hint={t('emp.hints.externalRef')}
            error={serverError('external_ref')}
          />
        </div>
        {mode === 'edit' ? (
          <TextAreaField
            label={t('emp.common.reason')}
            value={reason}
            onChange={setReason}
            maxLength={500}
            hint={t('emp.hints.correctionReason')}
            error={serverError('reason')}
          />
        ) : null}
        {nothingChanged ? (
          <p role="status" className="text-sm text-slate-700">
            {t('org.messages.noChanges')}
          </p>
        ) : null}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={mode === 'create' ? t('emp.actions.createEmployee') : t('org.actions.saveCorrection')}
        />
      </form>
    </Modal>
  )
}

// ----------------------------------------------------------- status change

/**
 * Active / On leave. Separation is never offered here: it has its own workflow
 * with an impact preview and explicit confirmations.
 */
export function StatusDialog({
  employee,
  onClose,
  onDone,
}: {
  employee: Employee
  onClose: () => void
  onDone: (employee: Employee) => void
}) {
  const { t } = useTranslation()
  const choices = (['active', 'on_leave'] as const).filter((value) => value !== employee.employment_status)
  const [status, setStatus] = useState<string>(choices.length === 1 ? choices[0] : '')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadEmployeesAndClose(onClose)
  const mutation = useEmployeeMutation((next: 'active' | 'on_leave') =>
    employeeService.changeStatus(employee.public_id, {
      version: employee.version,
      status: next,
      separation_date: null,
      end_open_records: false,
      end_direct_reports: false,
      reason: blankToNull(reason),
    }),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const statusError = status === '' ? t('org.errors.required') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (status !== 'active' && status !== 'on_leave') return
    mutation.mutate(status, { onSuccess: onDone })
  }

  return (
    <Modal
      title={t('emp.dialogs.statusTitle', { name: employee.full_name })}
      description={employee.employment_status === 'separated' ? t('emp.dialogs.statusRejoinHint') : t('emp.dialogs.statusHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-700">
          {t('emp.dialogs.currentStatus', {
            status: employee.employment_status ? t(`emp.status.${employee.employment_status}`) : t('emp.status.unknown'),
          })}
        </p>
        <SelectField
          label={t('emp.fields.newStatus')}
          value={status}
          onChange={setStatus}
          options={choices.map((value) => ({ value, label: t(`emp.status.${value}`) }))}
          emptyLabel={choices.length > 1 ? t('org.common.choose') : undefined}
          autoFocus
          required
          error={(showErrors ? statusError : undefined) ?? serverError('status')}
        />
        <TextAreaField
          label={t('emp.common.reason')}
          value={reason}
          onChange={setReason}
          maxLength={500}
          error={serverError('reason')}
        />
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.saveStatus')} />
      </form>
    </Modal>
  )
}
