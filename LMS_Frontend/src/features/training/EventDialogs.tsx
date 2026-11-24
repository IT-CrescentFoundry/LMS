import { LoaderCircle } from 'lucide-react'
import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { Modal } from '../../components/Modal'
import { EmployeePicker, LocationSelect, UnitSelect } from '../../components/Pickers'
import { trainingService } from '../../services/trainingService'
import {
  ATTENDANCE_STATUSES,
  COMPLETION_STATUSES,
  DELIVERY_MODES,
  type EmployeeRef,
  type EventBody,
  type EventStatus,
  type ParticipantsAddResult,
  type Participation,
  type Programme,
  type TrainingEvent,
  type TrainingSession,
} from '../../types/training'
import { useFeatureErrorMessage } from './trainingErrors'
import { useProgrammes, useTrainingMutation } from './trainingQueries'

// ------------------------------------------------------------------------ helpers

export function FormField({
  label,
  hint,
  children,
  id,
}: {
  label: string
  hint?: string
  children: ReactNode
  id: string
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
    </div>
  )
}

export function DialogError({ error }: { error: unknown }) {
  const message = useFeatureErrorMessage()
  if (!error) return null
  return (
    <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
      {message(error)}
    </p>
  )
}

export function DialogActions({
  busy,
  submitLabel,
  onCancel,
  danger = false,
}: {
  busy: boolean
  submitLabel: string
  onCancel: () => void
  danger?: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-4">
      <button type="button" onClick={onCancel} disabled={busy} className={secondaryButtonClassName}>
        {t('common.cancel')}
      </button>
      <button
        type="submit"
        disabled={busy}
        className={
          danger
            ? primaryButtonClassName.replace('bg-brand-700', 'bg-red-700').replace('hover:bg-brand-800', 'hover:bg-red-800')
            : primaryButtonClassName
        }
      >
        {busy ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
        {submitLabel}
      </button>
    </div>
  )
}

const text = (value: string): string | null => (value.trim() === '' ? null : value.trim())
const int = (value: string): number | null => (value.trim() === '' ? null : Number.parseInt(value, 10))

// --------------------------------------------------------------------- event form

interface EventDraft {
  title: string
  programme: string
  description: string
  delivery_mode: string
  org_unit: string
  location: string
  calendar_label: string
  dating: 'month' | 'dates'
  planned_month: string
  planned_start_date: string
  planned_end_date: string
  planned_duration_minutes: string
  venue: string
  online_join_url: string
  trainer_type: string
  trainer_employee: EmployeeRef[]
  trainer_name: string
  provider_name: string
  capacity: string
  planned_participant_count: string
  reported_attendance_count: string
  target_audience: string
  instructions: string
  code: string
  status: 'planned' | 'scheduled'
}

function draftOf(event: TrainingEvent | null): EventDraft {
  return {
    title: event?.title ?? '',
    programme: event?.programme?.public_id ?? '',
    description: event?.description ?? '',
    delivery_mode: event?.delivery_mode ?? '',
    org_unit: event?.org_unit?.public_id ?? '',
    location: event?.location?.public_id ?? '',
    calendar_label: event?.calendar_label ?? '',
    dating: event && event.planned_month && !event.planned_start_date ? 'month' : 'dates',
    planned_month: event?.planned_month?.slice(0, 7) ?? '',
    planned_start_date: event?.planned_start_date ?? '',
    planned_end_date: event?.planned_end_date ?? '',
    planned_duration_minutes: event?.planned_duration_minutes?.toString() ?? '',
    venue: event?.venue ?? '',
    online_join_url: event?.online_join_url ?? '',
    trainer_type: event?.trainer_type ?? '',
    trainer_employee: event?.trainer_employee ? [event.trainer_employee] : [],
    trainer_name: event?.trainer_name ?? '',
    provider_name: event?.provider_name ?? '',
    capacity: event?.capacity?.toString() ?? '',
    planned_participant_count: event?.planned_participant_count?.toString() ?? '',
    reported_attendance_count: event?.reported_attendance_count?.toString() ?? '',
    target_audience: event?.target_audience ?? '',
    instructions: event?.instructions ?? '',
    code: event?.code ?? '',
    status: 'planned',
  }
}

function bodyOf(draft: EventDraft): EventBody {
  const month = draft.dating === 'month' && draft.planned_month ? `${draft.planned_month}-01` : null
  return {
    title: text(draft.title),
    programme: text(draft.programme),
    description: text(draft.description),
    delivery_mode: text(draft.delivery_mode),
    org_unit: text(draft.org_unit),
    location: text(draft.location),
    calendar_label: text(draft.calendar_label),
    planned_month: month,
    planned_start_date: draft.dating === 'dates' ? text(draft.planned_start_date) : null,
    planned_end_date: draft.dating === 'dates' ? text(draft.planned_end_date) : null,
    planned_duration_minutes: int(draft.planned_duration_minutes),
    venue: text(draft.venue),
    online_join_url: text(draft.online_join_url),
    trainer_type: text(draft.trainer_type),
    trainer_employee: draft.trainer_type === 'internal' ? (draft.trainer_employee[0]?.public_id ?? null) : null,
    trainer_name: text(draft.trainer_name),
    provider_name: text(draft.provider_name),
    capacity: int(draft.capacity),
    planned_participant_count: int(draft.planned_participant_count),
    reported_attendance_count: int(draft.reported_attendance_count),
    target_audience: text(draft.target_audience),
    instructions: text(draft.instructions),
  }
}

/** Create (event = null) or edit an event. Edits send only the fields that changed. */
export function EventFormDialog({
  event,
  onClose,
  onSaved,
}: {
  event: TrainingEvent | null
  onClose: () => void
  onSaved: (event: TrainingEvent) => void
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<EventDraft>(() => draftOf(event))
  const programmes = useProgrammes({})
  const save = useTrainingMutation((body: EventBody) =>
    event === null
      ? trainingService.createEvent(body)
      : trainingService.updateEvent(event.public_id, { ...body, version: event.version }),
  )
  const ids = {
    title: useId(), programme: useId(), mode: useId(), label: useId(), month: useId(), start: useId(), end: useId(),
    duration: useId(), venue: useId(), url: useId(), trainerType: useId(), trainerName: useId(), provider: useId(),
    capacity: useId(), planned: useId(), reported: useId(), audience: useId(), instructions: useId(),
    description: useId(), code: useId(), status: useId(),
  }
  const set = <K extends keyof EventDraft>(key: K, value: EventDraft[K]) => setDraft((d) => ({ ...d, [key]: value }))

  function submit(e: FormEvent) {
    e.preventDefault()
    const body = bodyOf(draft)
    if (event === null) {
      const create: EventBody = {}
      for (const [key, value] of Object.entries(body)) if (value !== null) create[key] = value
      if (text(draft.code)) create.code = text(draft.code)
      create.status = draft.status
      save.mutate(create, { onSuccess: onSaved })
    } else {
      const original = bodyOf(draftOf(event))
      const changes: EventBody = {}
      for (const [key, value] of Object.entries(body)) if (original[key] !== value) changes[key] = value
      save.mutate(changes, { onSuccess: onSaved })
    }
  }

  const programmeOptions: Programme[] = programmes.data ?? []
  return (
    <Modal
      title={event === null ? t('training.form.createTitle') : t('training.form.editTitle')}
      description={t('training.form.description')}
      onClose={onClose}
      busy={save.isPending}
      size="lg"
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.programme} label={t('training.fields.programme')} hint={t('training.form.programmeHint')}>
            <select id={ids.programme} value={draft.programme} onChange={(e) => set('programme', e.target.value)} className={inputClassName()}>
              <option value="">{t('training.form.noProgramme')}</option>
              {programmeOptions.map((p) => (
                <option key={p.public_id} value={p.public_id}>
                  {p.title} ({p.code})
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.title} label={t('training.fields.title')}>
            <input id={ids.title} value={draft.title} onChange={(e) => set('title', e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          {event === null ? (
            <>
              <FormField id={ids.code} label={t('training.fields.code')} hint={t('training.form.codeHint')}>
                <input id={ids.code} value={draft.code} onChange={(e) => set('code', e.target.value)} maxLength={50} className={inputClassName()} />
              </FormField>
              <FormField id={ids.status} label={t('training.fields.status')}>
                <select id={ids.status} value={draft.status} onChange={(e) => set('status', e.target.value as 'planned' | 'scheduled')} className={inputClassName()}>
                  <option value="planned">{t('training.status.planned')}</option>
                  <option value="scheduled">{t('training.status.scheduled')}</option>
                </select>
              </FormField>
            </>
          ) : null}
          <FormField id={ids.mode} label={t('training.fields.deliveryMode')}>
            <select id={ids.mode} value={draft.delivery_mode} onChange={(e) => set('delivery_mode', e.target.value)} className={inputClassName()}>
              <option value="">{t('training.notRecorded')}</option>
              {DELIVERY_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {t(`training.mode.${mode}`)}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.label} label={t('training.fields.calendarLabel')} hint={t('training.form.calendarLabelHint')}>
            <input id={ids.label} value={draft.calendar_label} onChange={(e) => set('calendar_label', e.target.value)} maxLength={150} className={inputClassName()} />
          </FormField>
          <UnitSelect label={t('training.fields.orgUnit')} value={draft.org_unit} onChange={(v) => set('org_unit', v)} allLabel={t('common.none')} />
          <LocationSelect label={t('training.fields.location')} value={draft.location} onChange={(v) => set('location', v)} allLabel={t('common.none')} />
        </div>

        <fieldset className="space-y-3 rounded-lg border border-slate-200 p-4">
          <legend className="px-1 text-sm font-semibold text-slate-900">{t('training.form.plannedWhen')}</legend>
          <div className="flex flex-wrap gap-4 text-sm">
            {(['dates', 'month'] as const).map((mode) => (
              <label key={mode} className="flex items-center gap-2">
                <input type="radio" name="dating" checked={draft.dating === mode} onChange={() => set('dating', mode)} className="size-4 accent-brand-700" />
                {t(`training.form.dating.${mode}`)}
              </label>
            ))}
          </div>
          {draft.dating === 'month' ? (
            <FormField id={ids.month} label={t('training.fields.plannedMonth')}>
              <input id={ids.month} type="month" value={draft.planned_month} onChange={(e) => set('planned_month', e.target.value)} className={inputClassName()} />
            </FormField>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField id={ids.start} label={t('training.fields.plannedStart')}>
                <input id={ids.start} type="date" value={draft.planned_start_date} onChange={(e) => set('planned_start_date', e.target.value)} className={inputClassName()} />
              </FormField>
              <FormField id={ids.end} label={t('training.fields.plannedEnd')}>
                <input id={ids.end} type="date" value={draft.planned_end_date} onChange={(e) => set('planned_end_date', e.target.value)} className={inputClassName()} />
              </FormField>
            </div>
          )}
          <FormField id={ids.duration} label={t('training.fields.durationMinutes')}>
            <input id={ids.duration} type="number" min={1} value={draft.planned_duration_minutes} onChange={(e) => set('planned_duration_minutes', e.target.value)} className={inputClassName()} />
          </FormField>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.venue} label={t('training.fields.venue')}>
            <input id={ids.venue} value={draft.venue} onChange={(e) => set('venue', e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          <FormField id={ids.url} label={t('training.fields.onlineLink')} hint={t('training.form.onlineHint')}>
            <input id={ids.url} type="url" value={draft.online_join_url} onChange={(e) => set('online_join_url', e.target.value)} maxLength={500} className={inputClassName()} />
          </FormField>
          <FormField id={ids.trainerType} label={t('training.fields.trainerType')}>
            <select id={ids.trainerType} value={draft.trainer_type} onChange={(e) => set('trainer_type', e.target.value)} className={inputClassName()}>
              <option value="">{t('training.notRecorded')}</option>
              <option value="internal">{t('training.trainer.internal')}</option>
              <option value="external">{t('training.trainer.external')}</option>
            </select>
          </FormField>
          <FormField id={ids.trainerName} label={t('training.fields.trainerName')} hint={t('training.form.trainerNameHint')}>
            <input id={ids.trainerName} value={draft.trainer_name} onChange={(e) => set('trainer_name', e.target.value)} maxLength={200} className={inputClassName()} />
          </FormField>
          {draft.trainer_type === 'internal' ? (
            <div className="sm:col-span-2">
              <EmployeePicker label={t('training.fields.trainerEmployee')} selected={draft.trainer_employee} onChange={(v) => set('trainer_employee', v)} />
            </div>
          ) : null}
          <FormField id={ids.provider} label={t('training.fields.provider')}>
            <input id={ids.provider} value={draft.provider_name} onChange={(e) => set('provider_name', e.target.value)} maxLength={200} className={inputClassName()} />
          </FormField>
          <FormField id={ids.capacity} label={t('training.fields.capacity')}>
            <input id={ids.capacity} type="number" min={1} value={draft.capacity} onChange={(e) => set('capacity', e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.planned} label={t('training.fields.plannedCount')}>
            <input id={ids.planned} type="number" min={0} value={draft.planned_participant_count} onChange={(e) => set('planned_participant_count', e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.reported} label={t('training.fields.reportedCount')} hint={t('training.form.reportedHint')}>
            <input id={ids.reported} type="number" min={0} value={draft.reported_attendance_count} onChange={(e) => set('reported_attendance_count', e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.audience} label={t('training.fields.targetAudience')}>
            <input id={ids.audience} value={draft.target_audience} onChange={(e) => set('target_audience', e.target.value)} maxLength={500} className={inputClassName()} />
          </FormField>
        </div>
        <FormField id={ids.description} label={t('training.fields.description')}>
          <textarea id={ids.description} rows={2} value={draft.description} onChange={(e) => set('description', e.target.value)} className={inputClassName()} />
        </FormField>
        <FormField id={ids.instructions} label={t('training.fields.instructions')}>
          <textarea id={ids.instructions} rows={2} value={draft.instructions} onChange={(e) => set('instructions', e.target.value)} className={inputClassName()} />
        </FormField>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={event === null ? t('training.form.create') : t('common.save')} />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------- status dialog

export function StatusDialog({
  event,
  target,
  onClose,
}: {
  event: TrainingEvent
  target: EventStatus
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  const [start, setStart] = useState(event.actual_start_date ?? event.planned_start_date ?? '')
  const [end, setEnd] = useState(event.actual_end_date ?? '')
  const ids = { reason: useId(), start: useId(), end: useId() }
  const change = useTrainingMutation(() =>
    trainingService.changeStatus(event.public_id, {
      version: event.version,
      status: target,
      reason: text(reason),
      actual_start_date: target === 'completed' ? text(start) : undefined,
      actual_end_date: target === 'completed' ? text(end) : undefined,
    }),
  )
  const needsReason = target === 'cancelled' || target === 'postponed'
  return (
    <Modal
      title={t(`training.statusAction.${target}`)}
      description={t(`training.statusHelp.${target}`)}
      onClose={onClose}
      busy={change.isPending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          change.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={change.error} />
        {target === 'completed' ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField id={ids.start} label={t('training.fields.actualStart')}>
              <input id={ids.start} type="date" required value={start} onChange={(e) => setStart(e.target.value)} className={inputClassName()} />
            </FormField>
            <FormField id={ids.end} label={t('training.fields.actualEnd')}>
              <input id={ids.end} type="date" value={end} onChange={(e) => setEnd(e.target.value)} className={inputClassName()} />
            </FormField>
          </div>
        ) : null}
        {needsReason || target === 'completed' ? (
          <FormField id={ids.reason} label={needsReason ? t('training.fields.reasonRequired') : t('training.fields.reasonOptional')}>
            <textarea id={ids.reason} rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} className={inputClassName()} />
          </FormField>
        ) : null}
        <DialogActions
          busy={change.isPending}
          onCancel={onClose}
          submitLabel={t(`training.statusAction.${target}`)}
          danger={target === 'cancelled'}
        />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ session dialog

function localInput(iso: string | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function toIso(local: string): string | null {
  if (!local) return null
  const d = new Date(local)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

export function SessionDialog({
  event,
  session,
  onClose,
}: {
  event: TrainingEvent
  session: TrainingSession | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [starts, setStarts] = useState(localInput(session?.starts_at))
  const [ends, setEnds] = useState(localInput(session?.ends_at))
  const [venue, setVenue] = useState(session?.venue ?? '')
  const [url, setUrl] = useState(session?.online_join_url ?? '')
  const [notes, setNotes] = useState(session?.notes ?? '')
  const ids = { starts: useId(), ends: useId(), venue: useId(), url: useId(), notes: useId() }
  const save = useTrainingMutation(() => {
    const body = {
      starts_at: toIso(starts),
      ends_at: toIso(ends),
      venue: text(venue),
      online_join_url: text(url),
      notes: text(notes),
    }
    return session === null
      ? trainingService.addSession(event.public_id, body)
      : trainingService.updateSession(event.public_id, session.public_id, { ...body, version: session.version })
  })
  return (
    <Modal
      title={session === null ? t('training.sessions.add') : t('training.sessions.edit')}
      description={t('training.sessions.help')}
      onClose={onClose}
      busy={save.isPending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.starts} label={t('training.sessions.starts')}>
            <input id={ids.starts} type="datetime-local" required value={starts} onChange={(e) => setStarts(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.ends} label={t('training.sessions.ends')}>
            <input id={ids.ends} type="datetime-local" required value={ends} onChange={(e) => setEnds(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.venue} label={t('training.fields.venue')}>
            <input id={ids.venue} value={venue} onChange={(e) => setVenue(e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          <FormField id={ids.url} label={t('training.fields.onlineLink')}>
            <input id={ids.url} type="url" value={url} onChange={(e) => setUrl(e.target.value)} maxLength={500} className={inputClassName()} />
          </FormField>
        </div>
        <FormField id={ids.notes} label={t('training.sessions.notes')}>
          <input id={ids.notes} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} className={inputClassName()} />
        </FormField>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

/** Confirmation before cancelling a session. */
export function CancelSessionDialog({
  event,
  session,
  onClose,
}: {
  event: TrainingEvent
  session: TrainingSession
  onClose: () => void
}) {
  const { t } = useTranslation()
  const cancel = useTrainingMutation(() =>
    trainingService.updateSession(event.public_id, session.public_id, { version: session.version, status: 'cancelled' }),
  )
  return (
    <Modal title={t('training.sessions.cancelTitle')} description={t('training.sessions.cancelHelp')} onClose={onClose} busy={cancel.isPending}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          cancel.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
      >
        <DialogError error={cancel.error} />
        <DialogActions busy={cancel.isPending} onCancel={onClose} submitLabel={t('training.sessions.cancelConfirm')} danger />
      </form>
    </Modal>
  )
}

// --------------------------------------------------------------- participants

export function AddParticipantsDialog({ event, onClose }: { event: TrainingEvent; onClose: () => void }) {
  const { t } = useTranslation()
  const [employees, setEmployees] = useState<EmployeeRef[]>([])
  const [status, setStatus] = useState<'nominated' | 'confirmed'>('nominated')
  const [result, setResult] = useState<ParticipantsAddResult | null>(null)
  const statusId = useId()
  const add = useTrainingMutation(() =>
    trainingService.addParticipants(event.public_id, {
      employees: employees.map((e) => e.public_id),
      nomination_status: status,
    }),
  )
  if (result) {
    return (
      <Modal title={t('training.participants.addedTitle')} onClose={onClose}>
        <div className="space-y-3 text-sm">
          <p role="status">{t('training.participants.added', { count: result.added })}</p>
          {result.already_participating.length > 0 ? (
            <p>{t('training.participants.already', { codes: result.already_participating.join(', ') })}</p>
          ) : null}
          {result.employment_status_not_recorded.length > 0 ? (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
              {t('training.participants.statusUnrecorded', { codes: result.employment_status_not_recorded.join(', ') })}
            </p>
          ) : null}
          <div className="flex justify-end">
            <button type="button" onClick={onClose} className={primaryButtonClassName}>
              {t('common.close')}
            </button>
          </div>
        </div>
      </Modal>
    )
  }
  return (
    <Modal title={t('training.participants.addTitle')} description={t('training.participants.addHelp')} onClose={onClose} busy={add.isPending}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (employees.length === 0) return
          add.mutate(undefined, { onSuccess: setResult })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={add.error} />
        <EmployeePicker label={t('training.participants.employees')} selected={employees} onChange={setEmployees} multiple />
        <FormField id={statusId} label={t('training.participants.addAs')}>
          <select id={statusId} value={status} onChange={(e) => setStatus(e.target.value as 'nominated' | 'confirmed')} className={inputClassName()}>
            <option value="nominated">{t('training.nomination.nominated')}</option>
            <option value="confirmed">{t('training.nomination.confirmed')}</option>
          </select>
        </FormField>
        <DialogActions busy={add.isPending} onCancel={onClose} submitLabel={t('training.participants.addSubmit', { count: employees.length })} />
      </form>
    </Modal>
  )
}

/** Record nomination, attendance, completion, result, certificate and remarks. */
export function ParticipationDialog({
  event,
  participation,
  onClose,
}: {
  event: TrainingEvent
  participation: Participation
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [attendance, setAttendance] = useState(participation.attendance_status ?? '')
  const [minutes, setMinutes] = useState(participation.attended_minutes?.toString() ?? '')
  const [completion, setCompletion] = useState(participation.completion_status ?? '')
  const [result, setResultText] = useState(participation.assessment_result ?? '')
  const [certificate, setCertificate] = useState(participation.certificate_number ?? '')
  const [remarks, setRemarks] = useState(participation.remarks ?? '')
  const ids = { attendance: useId(), minutes: useId(), completion: useId(), result: useId(), certificate: useId(), remarks: useId() }
  const save = useTrainingMutation(() => {
    const body: Record<string, string | number | null> = { version: participation.version }
    const put = (key: string, value: string | number | null, before: string | number | null) => {
      if (value !== before) body[key] = value
    }
    put('attendance_status', text(attendance), participation.attendance_status)
    put('attended_minutes', int(minutes), participation.attended_minutes)
    put('completion_status', text(completion), participation.completion_status)
    put('assessment_result', text(result), participation.assessment_result)
    put('certificate_number', text(certificate), participation.certificate_number)
    put('remarks', text(remarks), participation.remarks)
    return trainingService.updateParticipation(event.public_id, participation.public_id, body)
  })
  return (
    <Modal
      title={t('training.participants.recordTitle', { name: participation.employee.name })}
      description={t('training.participants.recordHelp')}
      onClose={onClose}
      busy={save.isPending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.attendance} label={t('training.fields.attendance')}>
            <select id={ids.attendance} value={attendance} onChange={(e) => setAttendance(e.target.value)} className={inputClassName()}>
              <option value="">{t('training.notRecorded')}</option>
              {ATTENDANCE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {t(`training.attendance.${s}`)}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.minutes} label={t('training.fields.attendedMinutes')}>
            <input id={ids.minutes} type="number" min={0} value={minutes} onChange={(e) => setMinutes(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.completion} label={t('training.fields.completion')} hint={t('training.participants.completionHint')}>
            <select id={ids.completion} value={completion} onChange={(e) => setCompletion(e.target.value)} className={inputClassName()}>
              <option value="">{t('training.notRecorded')}</option>
              {COMPLETION_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {t(`training.completion.${s}`)}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.result} label={t('training.fields.assessmentResult')}>
            <input id={ids.result} value={result} onChange={(e) => setResultText(e.target.value)} maxLength={100} className={inputClassName()} />
          </FormField>
          <FormField id={ids.certificate} label={t('training.fields.certificate')}>
            <input id={ids.certificate} value={certificate} onChange={(e) => setCertificate(e.target.value)} maxLength={100} className={inputClassName()} />
          </FormField>
        </div>
        <FormField id={ids.remarks} label={t('training.fields.remarks')}>
          <textarea id={ids.remarks} rows={2} maxLength={1000} value={remarks} onChange={(e) => setRemarks(e.target.value)} className={inputClassName()} />
        </FormField>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

/** Confirmation before withdrawing a participant (nothing is deleted). */
export function WithdrawDialog({
  event,
  participation,
  onClose,
}: {
  event: TrainingEvent
  participation: Participation
  onClose: () => void
}) {
  const { t } = useTranslation()
  const withdraw = useTrainingMutation(() =>
    trainingService.updateParticipation(event.public_id, participation.public_id, {
      version: participation.version,
      nomination_status: 'withdrawn',
    }),
  )
  return (
    <Modal
      title={t('training.participants.withdrawTitle', { name: participation.employee.name })}
      description={t('training.participants.withdrawHelp')}
      onClose={onClose}
      busy={withdraw.isPending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          withdraw.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
      >
        <DialogError error={withdraw.error} />
        <DialogActions busy={withdraw.isPending} onCancel={onClose} submitLabel={t('training.participants.withdraw')} danger />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ programmes

export function ProgrammeDialog({ programme, onClose }: { programme: Programme | null; onClose: () => void }) {
  const { t } = useTranslation()
  const [code, setCode] = useState(programme?.code ?? '')
  const [title, setTitle] = useState(programme?.title ?? '')
  const [category, setCategory] = useState(programme?.category ?? '')
  const [mode, setMode] = useState(programme?.default_delivery_mode ?? '')
  const [duration, setDuration] = useState(programme?.standard_duration_minutes?.toString() ?? '')
  const [audience, setAudience] = useState(programme?.target_audience ?? '')
  const [objectives, setObjectives] = useState(programme?.objectives ?? '')
  const [description, setDescription] = useState(programme?.description ?? '')
  const [active, setActive] = useState(programme?.is_active ?? true)
  const ids = { code: useId(), title: useId(), category: useId(), mode: useId(), duration: useId(), audience: useId(), objectives: useId(), description: useId(), active: useId() }
  const save = useTrainingMutation(() => {
    const body: Record<string, string | number | boolean | null> = {
      code: code.trim(),
      title: title.trim(),
      category: text(category),
      default_delivery_mode: text(mode),
      standard_duration_minutes: int(duration),
      target_audience: text(audience),
      objectives: text(objectives),
      description: text(description),
    }
    if (programme === null) {
      const create: EventBody = {}
      for (const [key, value] of Object.entries(body)) if (value !== null && typeof value !== 'boolean') create[key] = value
      return trainingService.createProgramme(create)
    }
    return trainingService.updateProgramme(programme.public_id, { ...body, is_active: active, version: programme.version })
  })
  return (
    <Modal title={programme === null ? t('training.programmes.create') : t('training.programmes.edit')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.code} label={t('training.fields.code')}>
            <input id={ids.code} required value={code} onChange={(e) => setCode(e.target.value)} maxLength={50} className={inputClassName()} />
          </FormField>
          <FormField id={ids.title} label={t('training.fields.title')}>
            <input id={ids.title} required value={title} onChange={(e) => setTitle(e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          <FormField id={ids.category} label={t('training.fields.category')}>
            <input id={ids.category} value={category} onChange={(e) => setCategory(e.target.value)} maxLength={100} className={inputClassName()} />
          </FormField>
          <FormField id={ids.mode} label={t('training.fields.deliveryMode')}>
            <select id={ids.mode} value={mode} onChange={(e) => setMode(e.target.value)} className={inputClassName()}>
              <option value="">{t('training.notRecorded')}</option>
              {DELIVERY_MODES.map((m) => (
                <option key={m} value={m}>
                  {t(`training.mode.${m}`)}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.duration} label={t('training.fields.durationMinutes')}>
            <input id={ids.duration} type="number" min={1} value={duration} onChange={(e) => setDuration(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.audience} label={t('training.fields.targetAudience')}>
            <input id={ids.audience} value={audience} onChange={(e) => setAudience(e.target.value)} maxLength={500} className={inputClassName()} />
          </FormField>
        </div>
        <FormField id={ids.objectives} label={t('training.fields.objectives')}>
          <textarea id={ids.objectives} rows={2} value={objectives} onChange={(e) => setObjectives(e.target.value)} className={inputClassName()} />
        </FormField>
        <FormField id={ids.description} label={t('training.fields.description')}>
          <textarea id={ids.description} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} className={inputClassName()} />
        </FormField>
        {programme !== null ? (
          <label htmlFor={ids.active} className="flex items-center gap-2 text-sm">
            <input id={ids.active} type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="size-4 accent-brand-700" />
            {t('training.programmes.active')}
          </label>
        ) : null}
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}
