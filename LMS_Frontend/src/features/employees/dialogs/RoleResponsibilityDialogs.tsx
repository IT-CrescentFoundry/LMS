import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Modal } from '../../../components/Modal'
import { employeeService } from '../../../services/employeeService'
import type {
  Employee,
  ResponsibilityRecord,
  RoleRecord,
  RoleRecordKind,
} from '../../../types/employee'
import type { Ref } from '../../../types/organisation'
import { localName } from '../../organisation/names'
import { DialogActions, InfoNote, SelectField, TextAreaField, TextField } from '../../organisation/OrgParts'
import { useRolePicker } from '../../organisation/orgQueries'
import { lastDayToEnd } from '../dates'
import { useServerFieldErrors } from '../employeeErrorMessage'
import { useEmployeeMutation, useResponsibilityPicker } from '../employeeQueries'
import { EmployeeChangeError, LastDayField, LocationSelect, UnitSelect } from '../EmployeeFormParts'
import { blankToNull, lastDayBeforeStart } from '../formValues'
import { EndRecordDialog } from './EndRecordDialog'

function usePeriod() {
  const { t } = useTranslation()
  const [from, setFrom] = useState('')
  const [lastDay, setLastDay] = useState('')
  const errors = {
    from: from === '' ? t('org.errors.required') : undefined,
    lastDay: lastDayBeforeStart(from, lastDay) ? t('emp.validation.lastDayBeforeStart') : undefined,
  }
  return { from, setFrom, lastDay, setLastDay, errors, end: lastDay ? lastDayToEnd(lastDay) : null }
}

// ---------------------------------------------------------- functional roles

/**
 * Assign a functional role manually, or exclude a role the employee derives
 * from a designation (the derivation itself is the server's). Functional roles
 * describe work; they are never login permissions.
 */
export function RoleDialog({
  employee,
  kind,
  role,
  onClose,
  onDone,
}: {
  employee: Employee
  kind: RoleRecordKind
  /** Fixed role for an exclusion (the derived role being excluded). */
  role?: Ref
  onClose: () => void
  onDone: (record: RoleRecord) => void
}) {
  const { t, i18n } = useTranslation()
  const roles = useRolePicker(kind === 'manual')
  const [roleId, setRoleId] = useState(role?.public_id ?? '')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const period = usePeriod()
  const mutation = useEmployeeMutation(() =>
    employeeService.assignRole(employee.public_id, {
      functional_role_id: roleId,
      kind,
      effective_from: period.from,
      effective_to: period.end,
      reason: blankToNull(reason),
    }),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const roleError = roleId === '' ? t('org.errors.required') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (roleError || period.errors.from || period.errors.lastDay) return
    mutation.mutate(undefined, { onSuccess: onDone })
  }

  const options = (roles.data?.items ?? []).map((item) => ({
    value: item.public_id,
    label: `${localName(item, i18n.resolvedLanguage)} (${item.code})`,
  }))
  return (
    <Modal
      title={
        kind === 'manual'
          ? t('emp.dialogs.assignRoleTitle', { name: employee.full_name })
          : t('emp.dialogs.excludeRoleTitle', { role: role?.name ?? '' })
      }
      description={kind === 'manual' ? t('emp.dialogs.assignRoleHint') : t('emp.dialogs.excludeRoleHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <InfoNote>{t('emp.roles.note')}</InfoNote>
        {kind === 'manual' ? (
          <SelectField
            label={t('emp.fields.functionalRole')}
            value={roleId}
            onChange={setRoleId}
            options={options}
            emptyLabel={t('org.common.choose')}
            required
            error={(showErrors ? roleError : undefined) ?? serverError('functional_role_id')}
          />
        ) : (
          <p className="text-sm text-slate-800">
            {t('emp.dialogs.excludeRoleWhich', { role: role?.name ?? '', code: role?.code ?? '' })}
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('emp.fields.effectiveFrom')}
            type="date"
            value={period.from}
            onChange={period.setFrom}
            required
            error={(showErrors ? period.errors.from : undefined) ?? serverError('effective_from')}
            autoFocus={kind === 'exclusion'}
          />
          <LastDayField
            value={period.lastDay}
            onChange={period.setLastDay}
            error={(showErrors ? period.errors.lastDay : undefined) ?? serverError('effective_to')}
          />
        </div>
        <TextAreaField
          label={t('emp.common.reason')}
          value={reason}
          onChange={setReason}
          maxLength={500}
          error={serverError('reason')}
        />
        {mutation.isError ? <EmployeeChangeError error={mutation.error} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={kind === 'manual' ? t('emp.actions.assignRole') : t('emp.actions.excludeRole')}
        />
      </form>
    </Modal>
  )
}

export function EndRoleDialog({
  employee,
  record,
  onClose,
  onDone,
}: {
  employee: Employee
  record: RoleRecord
  onClose: () => void
  onDone: (lastDay: string) => void
}) {
  const { t } = useTranslation()
  return (
    <EndRecordDialog
      title={
        record.kind === 'manual'
          ? t('emp.dialogs.endRoleTitle', { role: record.functional_role.name })
          : t('emp.dialogs.endExclusionTitle', { role: record.functional_role.name })
      }
      description={record.kind === 'manual' ? t('emp.dialogs.endRoleHint') : t('emp.dialogs.endExclusionHint')}
      startedOn={record.effective_from}
      submitLabel={t('emp.actions.confirmEnd')}
      onSubmit={(body) => employeeService.endRole(employee.public_id, record.public_id, body)}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

// ---------------------------------------------------------- responsibilities

/** A responsibility (e.g. fire warden), optionally for one unit or location. */
export function ResponsibilityDialog({
  employee,
  onClose,
  onDone,
}: {
  employee: Employee
  onClose: () => void
  onDone: (record: ResponsibilityRecord) => void
}) {
  const { t, i18n } = useTranslation()
  const [filter, setFilter] = useState('')
  const picker = useResponsibilityPicker(filter.trim())
  const [responsibilityId, setResponsibilityId] = useState('')
  const [unitId, setUnitId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const period = usePeriod()
  const mutation = useEmployeeMutation(() =>
    employeeService.assignResponsibility(employee.public_id, {
      responsibility_id: responsibilityId,
      context_unit_id: unitId || null,
      context_location_id: locationId || null,
      effective_from: period.from,
      effective_to: period.end,
      reason: blankToNull(reason),
    }),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const responsibilityError = responsibilityId === '' ? t('org.errors.required') : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (responsibilityError || period.errors.from || period.errors.lastDay) return
    mutation.mutate(undefined, { onSuccess: onDone })
  }

  const options = (picker.data?.items ?? []).map((item) => ({
    value: item.public_id,
    label: `${localName(item, i18n.resolvedLanguage)} (${item.code})`,
  }))
  return (
    <Modal
      title={t('emp.dialogs.addResponsibilityTitle', { name: employee.full_name })}
      description={t('emp.dialogs.addResponsibilityHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <InfoNote>{t('emp.responsibilities.note')}</InfoNote>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('emp.fields.responsibilityFilter')}
            value={filter}
            onChange={setFilter}
            maxLength={100}
            autoFocus
          />
          <SelectField
            label={t('emp.fields.responsibility')}
            value={responsibilityId}
            onChange={setResponsibilityId}
            options={options}
            emptyLabel={t('org.common.choose')}
            required
            error={(showErrors ? responsibilityError : undefined) ?? serverError('responsibility_id')}
          />
          <UnitSelect
            label={t('emp.fields.contextUnit')}
            value={unitId}
            onChange={setUnitId}
            asOf={period.from}
            emptyLabel={t('emp.responsibilities.noContext')}
            error={serverError('context_unit_id')}
          />
          <LocationSelect label={t('emp.fields.contextLocation')} value={locationId} onChange={setLocationId} />
          <div aria-hidden="true" className="hidden sm:block" />
          <TextField
            label={t('emp.fields.effectiveFrom')}
            type="date"
            value={period.from}
            onChange={period.setFrom}
            required
            error={(showErrors ? period.errors.from : undefined) ?? serverError('effective_from')}
          />
          <LastDayField
            value={period.lastDay}
            onChange={period.setLastDay}
            error={(showErrors ? period.errors.lastDay : undefined) ?? serverError('effective_to')}
          />
        </div>
        <TextAreaField
          label={t('emp.common.reason')}
          value={reason}
          onChange={setReason}
          maxLength={500}
          error={serverError('reason')}
        />
        {mutation.isError ? <EmployeeChangeError error={mutation.error} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.addResponsibility')} />
      </form>
    </Modal>
  )
}

export function EndResponsibilityDialog({
  employee,
  record,
  onClose,
  onDone,
}: {
  employee: Employee
  record: ResponsibilityRecord
  onClose: () => void
  onDone: (lastDay: string) => void
}) {
  const { t } = useTranslation()
  return (
    <EndRecordDialog
      title={t('emp.dialogs.endResponsibilityTitle', { responsibility: record.responsibility.name })}
      description={t('emp.dialogs.endResponsibilityHint')}
      startedOn={record.effective_from}
      submitLabel={t('emp.actions.confirmEnd')}
      onSubmit={(body) => employeeService.endResponsibility(employee.public_id, record.public_id, body)}
      onClose={onClose}
      onDone={onDone}
    />
  )
}
