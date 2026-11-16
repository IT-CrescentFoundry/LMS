import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Modal } from '../../../components/Modal'
import { formatDate } from '../../../lib/format'
import { employeeService } from '../../../services/employeeService'
import {
  ASSIGNMENT_TYPES,
  type Assignment,
  type AssignmentChangeBody,
  type AssignmentCorrectionBody,
  type AssignmentType,
  type AssignmentWrite,
  type Employee,
} from '../../../types/employee'
import { DialogActions, SelectField, TextAreaField, TextField } from '../../organisation/OrgParts'
import { endToLastDay, lastDayToEnd } from '../dates'
import { useServerFieldErrors } from '../employeeErrorMessage'
import { serverFieldIssues } from '../employeeErrors'
import { useEmployeeMutation, useReloadEmployeesAndClose } from '../employeeQueries'
import { DesignationSelect, EmployeeChangeError, LastDayField, LocationSelect, RankedSelect, UnitSelect } from '../EmployeeFormParts'
import { blankToNull, lastDayBeforeStart } from '../formValues'
import { EndRecordDialog } from './EndRecordDialog'

interface Refs {
  unit: string
  designation: string
  grade: string
  level: string
  location: string
}

function refsOf(row?: Assignment): Refs {
  return {
    unit: row?.org_unit.public_id ?? '',
    designation: row?.designation?.public_id ?? '',
    grade: row?.grade?.public_id ?? '',
    level: row?.job_level?.public_id ?? '',
    location: row?.location?.public_id ?? '',
  }
}

/** Changed reference fields only (empty = cleared). */
function changedRefs(row: Assignment, refs: Refs) {
  const body: Partial<Pick<AssignmentChangeBody, 'org_unit_id' | 'designation_id' | 'grade_id' | 'job_level_id' | 'location_id'>> = {}
  if (refs.unit !== row.org_unit.public_id) body.org_unit_id = refs.unit
  if ((refs.designation || null) !== (row.designation?.public_id ?? null)) body.designation_id = refs.designation || null
  if ((refs.grade || null) !== (row.grade?.public_id ?? null)) body.grade_id = refs.grade || null
  if ((refs.level || null) !== (row.job_level?.public_id ?? null)) body.job_level_id = refs.level || null
  if ((refs.location || null) !== (row.location?.public_id ?? null)) body.location_id = refs.location || null
  return body
}

function RefFields({
  refs,
  setRefs,
  asOf,
  row,
  unitError,
}: {
  refs: Refs
  setRefs: (refs: Refs) => void
  asOf: string
  row?: Assignment
  unitError?: string
}) {
  const { t } = useTranslation()
  return (
    <>
      <UnitSelect
        label={t('emp.fields.unit')}
        value={refs.unit}
        onChange={(unit) => setRefs({ ...refs, unit })}
        asOf={asOf}
        current={row?.org_unit}
        required
        error={unitError}
      />
      <DesignationSelect
        value={refs.designation}
        onChange={(designation) => setRefs({ ...refs, designation })}
        current={row?.designation}
      />
      <div className="space-y-4">
        <RankedSelect kind="grades" value={refs.grade} onChange={(grade) => setRefs({ ...refs, grade })} current={row?.grade} />
        <RankedSelect kind="levels" value={refs.level} onChange={(level) => setRefs({ ...refs, level })} current={row?.job_level} />
        <LocationSelect
          value={refs.location}
          onChange={(location) => setRefs({ ...refs, location })}
          current={row?.location}
        />
      </div>
    </>
  )
}

function useTypeOptions() {
  const { t } = useTranslation()
  return ASSIGNMENT_TYPES.map((value) => ({ value, label: t(`emp.assignmentTypes.${value}`) }))
}

// --------------------------------------------------------------------- add

export function AddAssignmentDialog({
  employee,
  onClose,
  onDone,
}: {
  employee: Employee
  onClose: () => void
  onDone: (result: AssignmentWrite) => void
}) {
  const { t } = useTranslation()
  const typeOptions = useTypeOptions()
  const [type, setType] = useState<AssignmentType>('primary')
  const [refs, setRefs] = useState<Refs>(refsOf())
  const [from, setFrom] = useState('')
  const [lastDay, setLastDay] = useState('')
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const mutation = useEmployeeMutation(() =>
    employeeService.createAssignment(employee.public_id, {
      assignment_type: type,
      org_unit_id: refs.unit,
      designation_id: refs.designation || null,
      grade_id: refs.grade || null,
      job_level_id: refs.level || null,
      location_id: refs.location || null,
      effective_from: from,
      effective_to: lastDay ? lastDayToEnd(lastDay) : null,
      reason: blankToNull(reason),
    }),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const required = t('org.errors.required')
  const errors = {
    unit: refs.unit === '' ? required : undefined,
    from: from === '' ? required : undefined,
    lastDay: lastDayBeforeStart(from, lastDay) ? t('emp.validation.lastDayBeforeStart') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.unit || errors.from || errors.lastDay) return
    mutation.mutate(undefined, { onSuccess: onDone })
  }

  return (
    <Modal
      title={t('emp.dialogs.addAssignmentTitle', { name: employee.full_name })}
      description={t('emp.dialogs.addAssignmentHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label={t('emp.fields.assignmentType')}
            value={type}
            onChange={(value) => setType(value as AssignmentType)}
            options={typeOptions}
            required
            hint={t('emp.hints.assignmentType')}
            error={serverError('assignment_type')}
          />
          <TextField
            label={t('emp.fields.effectiveFrom')}
            type="date"
            value={from}
            onChange={setFrom}
            required
            hint={t('emp.hints.effectiveFrom')}
            error={(showErrors ? errors.from : undefined) ?? serverError('effective_from')}
          />
          <RefFields
            refs={refs}
            setRefs={setRefs}
            asOf={from}
            unitError={(showErrors ? errors.unit : undefined) ?? serverError('org_unit_id')}
          />
          <LastDayField
            value={lastDay}
            onChange={setLastDay}
            error={(showErrors ? errors.lastDay : undefined) ?? serverError('effective_to')}
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
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.addAssignment')} />
      </form>
    </Modal>
  )
}

// ---------------------------------------------------------- change from date

/**
 * A business change (transfer, promotion, new location) from a date: the current
 * row ends the day before and a new row starts - history is kept.
 */
export function ChangeAssignmentDialog({
  employee,
  row,
  onClose,
  onDone,
}: {
  employee: Employee
  row: Assignment
  onClose: () => void
  onDone: (result: AssignmentWrite, effectiveDate: string) => void
}) {
  const { t, i18n } = useTranslation()
  const [effectiveDate, setEffectiveDate] = useState('')
  const [refs, setRefs] = useState<Refs>(refsOf(row))
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const [nothingChanged, setNothingChanged] = useState(false)
  const reload = useReloadEmployeesAndClose(onClose)
  const mutation = useEmployeeMutation((body: AssignmentChangeBody) =>
    employeeService.changeAssignment(employee.public_id, row.public_id, body),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const required = t('org.errors.required')
  const errors = {
    date:
      effectiveDate === ''
        ? required
        : row.effective_from && effectiveDate <= row.effective_from
          ? t('emp.validation.changeAfterStart')
          : undefined,
    unit: refs.unit === '' ? required : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.date || errors.unit) return
    const changes = changedRefs(row, refs)
    if (Object.keys(changes).length === 0) {
      setNothingChanged(true)
      return
    }
    setNothingChanged(false)
    mutation.mutate(
      { version: row.version, effective_date: effectiveDate, reason: blankToNull(reason), ...changes },
      { onSuccess: (result) => onDone(result, effectiveDate) },
    )
  }

  return (
    <Modal
      title={t('emp.dialogs.changeAssignmentTitle', { unit: row.org_unit.name })}
      description={t('emp.dialogs.changeAssignmentHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-700">
          {t('emp.dialogs.currentAssignment', {
            type: t(`emp.assignmentTypes.${row.assignment_type}`),
            unit: row.org_unit.name,
            from: row.effective_from ? formatDate(row.effective_from, i18n.resolvedLanguage) : t('emp.common.startNotRecorded'),
          })}
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('emp.fields.changeDate')}
            type="date"
            value={effectiveDate}
            onChange={setEffectiveDate}
            required
            hint={t('emp.hints.changeDate')}
            error={(showErrors ? errors.date : undefined) ?? serverError('effective_date')}
            autoFocus
          />
          <div aria-hidden="true" className="hidden sm:block" />
          <RefFields
            refs={refs}
            setRefs={setRefs}
            asOf={effectiveDate}
            row={row}
            unitError={(showErrors ? errors.unit : undefined) ?? serverError('org_unit_id')}
          />
        </div>
        <TextAreaField
          label={t('emp.common.reason')}
          value={reason}
          onChange={setReason}
          maxLength={500}
          error={serverError('reason')}
        />
        {nothingChanged ? (
          <p role="status" className="text-sm text-slate-700">
            {t('org.messages.noChanges')}
          </p>
        ) : null}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('emp.actions.saveChange')} />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ correct

/**
 * Correction of wrongly recorded data (type, references or dates). It rewrites
 * the record, so a reason is mandatory and an explicit confirmation is required.
 */
export function CorrectAssignmentDialog({
  employee,
  row,
  onClose,
  onDone,
}: {
  employee: Employee
  row: Assignment
  onClose: () => void
  onDone: (result: AssignmentWrite) => void
}) {
  const { t } = useTranslation()
  const typeOptions = useTypeOptions()
  const [type, setType] = useState<AssignmentType>(row.assignment_type)
  const [refs, setRefs] = useState<Refs>(refsOf(row))
  const [from, setFrom] = useState(row.effective_from ?? '')
  const [lastDay, setLastDay] = useState(endToLastDay(row.effective_to) ?? '')
  const [reason, setReason] = useState('')
  const [step, setStep] = useState<'form' | 'confirm'>('form')
  const [showErrors, setShowErrors] = useState(false)
  const [nothingChanged, setNothingChanged] = useState(false)
  const reload = useReloadEmployeesAndClose(onClose)
  const mutation = useEmployeeMutation((body: AssignmentCorrectionBody) =>
    employeeService.correctAssignment(employee.public_id, row.public_id, body),
  )
  const serverError = useServerFieldErrors(mutation.error)
  const required = t('org.errors.required')
  const errors = {
    unit: refs.unit === '' ? required : undefined,
    reason: reason.trim() === '' ? t('emp.validation.correctionReason') : undefined,
    lastDay: lastDayBeforeStart(from, lastDay) ? t('emp.validation.lastDayBeforeStart') : undefined,
  }

  function build(): AssignmentCorrectionBody | null {
    const body: Omit<AssignmentCorrectionBody, 'version' | 'reason'> = { ...changedRefs(row, refs) }
    if (type !== row.assignment_type) body.assignment_type = type
    if ((from || null) !== row.effective_from) body.effective_from = from || null
    const end = lastDay ? lastDayToEnd(lastDay) : null
    if (end !== row.effective_to) body.effective_to = end
    if (Object.keys(body).length === 0) return null
    return { version: row.version, reason: reason.trim(), ...body }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'form') {
      setShowErrors(true)
      if (errors.unit || errors.reason || errors.lastDay) return
      if (build() === null) {
        setNothingChanged(true)
        return
      }
      setNothingChanged(false)
      setStep('confirm')
      return
    }
    const body = build()
    if (body) {
      mutation.mutate(body, {
        onSuccess: onDone,
        // Field problems are shown on the fields: go back to the form.
        onError: (error) => {
          if (serverFieldIssues(error).size > 0) setStep('form')
        },
      })
    }
  }

  return (
    <Modal
      title={t('emp.dialogs.correctAssignmentTitle', { unit: row.org_unit.name })}
      description={t('emp.dialogs.correctAssignmentHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {step === 'form' ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <SelectField
                label={t('emp.fields.assignmentType')}
                value={type}
                onChange={(value) => setType(value as AssignmentType)}
                options={typeOptions}
                required
              />
              <div aria-hidden="true" className="hidden sm:block" />
              <TextField
                label={t('emp.fields.effectiveFrom')}
                type="date"
                value={from}
                onChange={setFrom}
                error={serverError('effective_from')}
              />
              <LastDayField
                value={lastDay}
                onChange={setLastDay}
                error={(showErrors ? errors.lastDay : undefined) ?? serverError('effective_to')}
              />
              <RefFields
                refs={refs}
                setRefs={setRefs}
                asOf={from}
                row={row}
                unitError={(showErrors ? errors.unit : undefined) ?? serverError('org_unit_id')}
              />
            </div>
            <TextAreaField
              label={t('emp.fields.correctionReason')}
              value={reason}
              onChange={setReason}
              maxLength={500}
              required
              hint={t('emp.hints.correctionReason')}
              error={(showErrors ? errors.reason : undefined) ?? serverError('reason')}
            />
            {nothingChanged ? (
              <p role="status" className="text-sm text-slate-700">
                {t('org.messages.noChanges')}
              </p>
            ) : null}
          </>
        ) : (
          <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
            <p className="font-medium">{t('emp.dialogs.correctAssignmentConfirm')}</p>
            <p>{t('emp.dialogs.correctAssignmentWarning')}</p>
          </div>
        )}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={step === 'confirm' && !mutation.isPending ? () => setStep('form') : onClose}
          cancelLabel={step === 'confirm' ? t('org.actions.back') : undefined}
          busy={mutation.isPending}
          tone={step === 'confirm' ? 'danger' : 'primary'}
          submitLabel={step === 'form' ? t('org.actions.continue') : t('emp.actions.confirmCorrection')}
        />
      </form>
    </Modal>
  )
}

// --------------------------------------------------------------------- end

export function EndAssignmentDialog({
  employee,
  row,
  onClose,
  onDone,
}: {
  employee: Employee
  row: Assignment
  onClose: () => void
  onDone: (lastDay: string) => void
}) {
  const { t } = useTranslation()
  return (
    <EndRecordDialog
      title={t('emp.dialogs.endAssignmentTitle', { unit: row.org_unit.name })}
      description={t('emp.dialogs.endAssignmentHint')}
      startedOn={row.effective_from}
      submitLabel={t('emp.actions.confirmEnd')}
      onSubmit={(body) => employeeService.endAssignment(employee.public_id, row.public_id, { version: row.version, ...body })}
      onClose={onClose}
      onDone={onDone}
    />
  )
}
