import { useState, type FormEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../../components/LoadingState'
import { Modal } from '../../../components/Modal'
import { ApiError } from '../../../lib/apiClient'
import { formatDate } from '../../../lib/format'
import { employeeService } from '../../../services/employeeService'
import type { DirectReport, Employee, SeparationPreview, SeparationRecord, StatusChangeBody } from '../../../types/employee'
import { primaryButtonClassName, secondaryButtonClassName } from '../../../components/formStyles'
import { CheckboxField, TextAreaField, TextField } from '../../organisation/OrgParts'
import { dayAfter, endToLastDay } from '../dates'
import { useEmployeeMutation, useReloadEmployeesAndClose, useSeparationPreview } from '../employeeQueries'
import { EmployeeChangeError } from '../EmployeeFormParts'
import { blankToNull } from '../formValues'

type Step = 'date' | 'impact' | 'confirm'

const DANGER_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-md bg-red-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70'

/**
 * Separation in three steps:
 *  1. the LAST WORKING DAY (sent unchanged - the server ends records on the
 *     following day because end dates are exclusive);
 *  2. the read-only impact preview: the employee's own records, their direct
 *     reports (a separate panel and a separate confirmation), and records that
 *     cannot be ended automatically (these block submission);
 *  3. a final confirmation, then the POST.
 * Nothing is pre-ticked, nothing is detached silently and nothing is retried: a
 * 409 after the preview shows the server's blockers and refreshes the preview.
 */
export function SeparationDialog({
  employee,
  onClose,
  onDone,
}: {
  employee: Employee
  onClose: () => void
  onDone: (employee: Employee, lastWorkingDay: string) => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [step, setStep] = useState<Step>('date')
  const [lastWorkingDay, setLastWorkingDay] = useState('')
  const [reason, setReason] = useState('')
  const [endOwn, setEndOwn] = useState(false)
  const [endReports, setEndReports] = useState(false)
  const [showErrors, setShowErrors] = useState(false)
  const [staleError, setStaleError] = useState<unknown>(null)
  const reload = useReloadEmployeesAndClose(onClose)
  const preview = useSeparationPreview(employee.public_id, lastWorkingDay, step !== 'date')
  const mutation = useEmployeeMutation((body: StatusChangeBody) =>
    employeeService.changeStatus(employee.public_id, body),
  )

  const dateError =
    lastWorkingDay === ''
      ? t('org.errors.required')
      : employee.date_of_joining && lastWorkingDay < employee.date_of_joining
        ? t('emp.validation.separationBeforeJoining')
        : undefined
  const data = preview.data
  const own = data?.own_records.filter((record) => !record.starts_after_separation) ?? []
  const reports = data?.direct_reports.filter((record) => !record.starts_after_separation) ?? []
  const blocking = [
    ...(data?.own_records.filter((record) => record.starts_after_separation) ?? []),
    ...(data?.direct_reports.filter((record) => record.starts_after_separation) ?? []),
  ]
  const confirmationsMissing =
    !data ||
    data.blocked ||
    (data.requires_end_open_records && !endOwn) ||
    (data.requires_end_direct_reports && !endReports)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'date') {
      setShowErrors(true)
      if (dateError) return
      setEndOwn(false)
      setEndReports(false)
      setStaleError(null)
      setStep('impact')
      return
    }
    if (step === 'impact') {
      if (confirmationsMissing) return
      setStep('confirm')
      return
    }
    if (!data) return
    mutation.mutate(
      {
        version: employee.version,
        status: 'separated',
        separation_date: lastWorkingDay, // the last working day, exactly as entered
        end_open_records: data.requires_end_open_records && endOwn,
        end_direct_reports: data.requires_end_direct_reports && endReports,
        reason: blankToNull(reason),
      },
      {
        onSuccess: (result) => onDone(result, lastWorkingDay),
        onError: (error) => {
          if (error instanceof ApiError && error.code === 'open_records_on_separation') {
            // Records changed since the preview: show what the server listed, refresh
            // the impact and ask for the confirmations again. Never retried.
            setStaleError(error)
            setEndOwn(false)
            setEndReports(false)
            setStep('impact')
            mutation.reset()
            void preview.refetch()
          }
        },
      },
    )
  }

  const nextDay = lastWorkingDay ? formatDate(dayAfter(lastWorkingDay), language) : ''
  let content: ReactNode
  if (step === 'date') {
    content = (
      <>
        <TextField
          label={t('emp.separation.lastWorkingDay')}
          type="date"
          value={lastWorkingDay}
          onChange={setLastWorkingDay}
          required
          hint={t('emp.separation.lastWorkingDayHint')}
          error={showErrors ? dateError : undefined}
          autoFocus
        />
        {lastWorkingDay ? (
          <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-800 ring-1 ring-slate-200" aria-live="polite">
            {t('emp.separation.recordsEndOn', { nextDay })}
          </p>
        ) : null}
        <TextAreaField label={t('emp.common.reason')} value={reason} onChange={setReason} maxLength={500} />
      </>
    )
  } else if (preview.isPending) {
    content = <LoadingState />
  } else if (preview.isError) {
    content = <EmployeeChangeError error={preview.error} />
  } else if (data) {
    content =
      step === 'impact' ? (
        <ImpactStep
          data={data}
          own={own}
          reports={reports}
          blocking={blocking}
          endOwn={endOwn}
          setEndOwn={setEndOwn}
          endReports={endReports}
          setEndReports={setEndReports}
          staleError={staleError}
        />
      ) : (
        <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-950">
          <p className="font-medium">
            {t('emp.separation.confirmText', {
              name: employee.full_name,
              code: employee.employee_code,
              lastDay: formatDate(data.separation_date, language),
            })}
          </p>
          <ul className="list-disc space-y-0.5 pl-5">
            <li>{t('emp.separation.confirmOwn', { count: own.length, date: formatDate(data.records_end_on, language) })}</li>
            <li>
              {t('emp.separation.confirmReports', { count: reports.length, date: formatDate(data.records_end_on, language) })}
            </li>
          </ul>
          <p>{t('emp.separation.confirmAccount')}</p>
        </div>
      )
  }

  const busy = mutation.isPending
  return (
    <Modal
      title={t('emp.separation.title', { name: employee.full_name })}
      description={t(`emp.separation.step.${step}`)}
      onClose={onClose}
      busy={busy}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {content}
        {mutation.isError ? <EmployeeChangeError error={mutation.error} onReload={reload} /> : null}
        {/* Own footer: only the submit button waits for the required confirmations. */}
        <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={() => {
              if (step === 'date') {
                onClose()
                return
              }
              setStep(step === 'confirm' ? 'impact' : 'date')
              mutation.reset()
            }}
            disabled={busy}
            className={secondaryButtonClassName}
          >
            {step === 'date' ? t('org.actions.cancel') : t('org.actions.back')}
          </button>
          <button
            type="submit"
            disabled={busy || (step !== 'date' && (preview.isFetching || confirmationsMissing))}
            aria-busy={busy || undefined}
            className={step === 'confirm' ? DANGER_BUTTON : primaryButtonClassName}
          >
            {busy
              ? t('org.actions.saving')
              : step === 'date'
                ? t('emp.separation.checkImpact')
                : step === 'impact'
                  ? t('org.actions.continue')
                  : t('emp.separation.confirm')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ImpactStep({
  data,
  own,
  reports,
  blocking,
  endOwn,
  setEndOwn,
  endReports,
  setEndReports,
  staleError,
}: {
  data: SeparationPreview
  own: SeparationRecord[]
  reports: DirectReport[]
  blocking: (SeparationRecord | DirectReport)[]
  endOwn: boolean
  setEndOwn: (value: boolean) => void
  endReports: boolean
  setEndReports: (value: boolean) => void
  staleError: unknown
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const endsOn = formatDate(data.records_end_on, language)
  const nothing = own.length === 0 && reports.length === 0 && blocking.length === 0
  return (
    <div className="space-y-4">
      {staleError ? (
        <div className="space-y-2">
          <EmployeeChangeError error={staleError} />
          <p className="text-sm font-medium text-slate-800">{t('emp.separation.refreshed')}</p>
        </div>
      ) : null}
      <p className="text-sm text-slate-800">
        {t('emp.separation.impactIntro', { lastDay: formatDate(data.separation_date, language), endsOn })}
      </p>
      {nothing ? (
        <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950">
          {t('emp.separation.nothingContinues')}
        </p>
      ) : null}

      {own.length > 0 ? (
        <section aria-labelledby="sep-own" className="space-y-3 rounded-lg border border-slate-200 p-3">
          <h3 id="sep-own" className="font-semibold text-slate-900">
            {t('emp.separation.ownTitle')}
          </h3>
          <ul className="space-y-1 text-sm">
            {own.map((record) => (
              <li key={record.record_id} className="break-words text-slate-800">
                <OwnRecordLine record={record} />
              </li>
            ))}
          </ul>
          <CheckboxField
            label={t('emp.separation.endOwn', { count: own.length, date: endsOn })}
            checked={endOwn}
            onChange={setEndOwn}
          />
        </section>
      ) : null}

      {reports.length > 0 ? (
        <section aria-labelledby="sep-reports" className="space-y-3 rounded-lg border-2 border-amber-300 bg-amber-50 p-3">
          <h3 id="sep-reports" className="font-semibold text-amber-950">
            {t('emp.separation.reportsTitle')}
          </h3>
          <ul className="space-y-1 text-sm">
            {reports.map((record) => (
              <li key={record.record_id} className="break-words text-amber-950">
                {t('emp.separation.reportLine', {
                  code: record.employee.employee_code,
                  name: record.employee.full_name,
                  since: record.effective_from ? formatDate(record.effective_from, language) : t('emp.common.startNotRecorded'),
                })}
              </li>
            ))}
          </ul>
          <CheckboxField
            label={t('emp.separation.endReports', { count: reports.length, date: endsOn })}
            checked={endReports}
            onChange={setEndReports}
          />
        </section>
      ) : null}

      {blocking.length > 0 ? (
        <section aria-labelledby="sep-blocked" className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3">
          <h3 id="sep-blocked" className="font-semibold text-red-950">
            {t('emp.separation.blockedTitle')}
          </h3>
          <ul className="list-disc space-y-0.5 pl-5 text-sm text-red-950">
            {blocking.map((record) => (
              <li key={record.record_id} className="break-words">
                {'kind' in record ? (
                  <OwnRecordLine record={record} />
                ) : (
                  t('emp.separation.reportLine', {
                    code: record.employee.employee_code,
                    name: record.employee.full_name,
                    since: record.effective_from ? formatDate(record.effective_from, language) : t('emp.common.startNotRecorded'),
                  })
                )}
              </li>
            ))}
          </ul>
          <p className="text-sm text-red-950">{t('emp.separation.blockedHelp')}</p>
        </section>
      ) : null}
    </div>
  )
}

function OwnRecordLine({ record }: { record: SeparationRecord }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const from = record.effective_from ? formatDate(record.effective_from, language) : t('emp.common.startNotRecorded')
  const lastDay = endToLastDay(record.effective_to)
  const period = lastDay
    ? t('emp.separation.periodEnding', { from, lastDay: formatDate(lastDay, language) })
    : t('emp.separation.periodOpen', { from })
  if (record.kind === 'reporting_line') {
    return <>{t('emp.separation.reportsTo', { code: record.code, name: record.name, period })}</>
  }
  return (
    <>
      {t(`emp.separation.kinds.${record.kind}`)}: <span className="font-medium">{record.name}</span>{' '}
      <span className="font-mono text-xs">{record.code}</span> — {period}
    </>
  )
}
