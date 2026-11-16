import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Modal } from '../../../components/Modal'
import { formatDate } from '../../../lib/format'
import { DialogActions, TextAreaField } from '../../organisation/OrgParts'
import { lastDayToEnd } from '../dates'
import { useServerFieldErrors } from '../employeeErrorMessage'
import { serverFieldIssues } from '../employeeErrors'
import { useEmployeeMutation, useReloadEmployeesAndClose } from '../employeeQueries'
import { EmployeeChangeError, LastDayField } from '../EmployeeFormParts'
import { blankToNull, lastDayBeforeStart } from '../formValues'

/**
 * Ends an assignment, functional-role record, responsibility or reporting line.
 * The user enters the LAST DAY IN EFFECT; the request carries the exclusive
 * `effective_to` (the following day) built by `lastDayToEnd` - only here.
 */
export function EndRecordDialog({
  title,
  description,
  startedOn,
  submitLabel,
  onSubmit,
  onClose,
  onDone,
}: {
  title: string
  description: string
  /** The record's start: the last day may not precede it. */
  startedOn: string | null
  submitLabel: string
  onSubmit: (body: { effective_to: string; reason: string | null }) => Promise<unknown>
  onClose: () => void
  onDone: (lastDay: string) => void
}) {
  const { t, i18n } = useTranslation()
  const [lastDay, setLastDay] = useState('')
  const [reason, setReason] = useState('')
  const [step, setStep] = useState<'form' | 'confirm'>('form')
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReloadEmployeesAndClose(onClose)
  const mutation = useEmployeeMutation(onSubmit)
  const serverError = useServerFieldErrors(mutation.error)
  const error =
    lastDay === ''
      ? t('org.errors.required')
      : startedOn && lastDayBeforeStart(startedOn, lastDay)
        ? t('emp.validation.lastDayBeforeStart')
        : undefined

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'form') {
      setShowErrors(true)
      if (error) return
      setStep('confirm')
      return
    }
    mutation.mutate(
      { effective_to: lastDayToEnd(lastDay), reason: blankToNull(reason) },
      {
        onSuccess: () => onDone(lastDay),
        onError: (failure) => {
          if (serverFieldIssues(failure).size > 0) setStep('form')
        },
      },
    )
  }

  const language = i18n.resolvedLanguage
  return (
    <Modal title={title} description={description} onClose={onClose} busy={mutation.isPending}>
      <form noValidate onSubmit={submit} className="space-y-4">
        {step === 'form' ? (
          <>
            <LastDayField
              value={lastDay}
              onChange={setLastDay}
              required
              error={(showErrors ? error : undefined) ?? serverError('effective_to')}
              autoFocus
            />
            <TextAreaField
              label={t('emp.common.reason')}
              value={reason}
              onChange={setReason}
              maxLength={500}
              error={serverError('reason')}
            />
          </>
        ) : (
          <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
            <p className="font-medium">
              {t('emp.dialogs.endConfirm', {
                lastDay: formatDate(lastDay, language),
                end: formatDate(lastDayToEnd(lastDay), language),
              })}
            </p>
            <p>{t('emp.dialogs.historyKept')}</p>
          </div>
        )}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={step === 'confirm' && !mutation.isPending ? () => setStep('form') : onClose}
          cancelLabel={step === 'confirm' ? t('org.actions.back') : undefined}
          busy={mutation.isPending}
          tone={step === 'confirm' ? 'danger' : 'primary'}
          submitLabel={step === 'form' ? t('org.actions.continue') : submitLabel}
        />
      </form>
    </Modal>
  )
}
