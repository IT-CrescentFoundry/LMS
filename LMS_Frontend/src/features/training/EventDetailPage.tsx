import { ChevronRight, Pencil, Plus, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import {
  cardClassName,
  EmptyState,
  FeatureError,
  Field,
  tableClassName,
  tableWrapClassName,
  tdClassName,
  thClassName,
} from '../../components/FeatureState'
import { primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDate, formatDateTime } from '../../lib/format'
import {
  STATUS_TRANSITIONS,
  type EventStatus,
  type Participation,
  type TrainingEvent,
  type TrainingSession,
} from '../../types/training'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import {
  AddParticipantsDialog,
  CancelSessionDialog,
  EventFormDialog,
  ParticipationDialog,
  SessionDialog,
  StatusDialog,
  WithdrawDialog,
} from './EventDialogs'
import { AttendanceBadge, CompletionBadge, EventStatusBadge, NominationBadge, TimeframeBadge } from './TrainingParts'
import { useDeliveryModeLabel, useDurationText, useWhenText } from './trainingLabels'
import { useEvent, useParticipants } from './trainingQueries'

type DialogState =
  | { kind: 'edit' }
  | { kind: 'status'; target: EventStatus }
  | { kind: 'session'; session: TrainingSession | null }
  | { kind: 'cancelSession'; session: TrainingSession }
  | { kind: 'add' }
  | { kind: 'record'; participation: Participation }
  | { kind: 'withdraw'; participation: Participation }

/** One training event: planned vs actual details, sessions and participants. */
export function EventDetailPage() {
  const { t } = useTranslation()
  const { eventId = '' } = useParams()
  const event = useEvent(eventId)
  const canManage = useHasPermission(PERMISSIONS.TRAINING_EVENTS_MANAGE)
  const [dialog, setDialog] = useState<DialogState | null>(null)

  if (event.isPending) return <LoadingState />
  if (event.isError) {
    return <FeatureError error={event.error} title={t('training.event.loadError')} onRetry={() => void event.refetch()} />
  }
  const data = event.data
  const close = () => setDialog(null)
  const editable = canManage && data.status !== 'cancelled'
  const sessionsEditable = canManage && data.status !== 'cancelled' && data.status !== 'completed'

  return (
    <div className="space-y-6">
      <nav aria-label={t('org.breadcrumb')}>
        <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-600">
          <li>
            <Link to="/training" className="hover:text-brand-700 hover:underline">
              {t('nav.trainingRecords')}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-4 text-slate-400" />
          </li>
          <li aria-current="page" className="font-medium text-slate-900">
            {data.code}
          </li>
        </ol>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-bold break-words text-slate-900">{data.title}</h1>
          <div className="flex flex-wrap gap-2">
            <EventStatusBadge status={data.status} />
            <TimeframeBadge timeframe={data.timeframe} />
          </div>
          {data.status_reason ? (
            <p className="text-sm text-slate-600">{t('training.event.reason', { reason: data.status_reason })}</p>
          ) : null}
        </div>
        {canManage ? (
          <div className="flex flex-wrap gap-2" role="group" aria-label={t('training.event.actions')}>
            {editable ? (
              <button type="button" onClick={() => setDialog({ kind: 'edit' })} className={secondaryButtonClassName}>
                <Pencil aria-hidden="true" className="size-4" />
                {t('training.event.edit')}
              </button>
            ) : null}
            {STATUS_TRANSITIONS[data.status].map((target) => (
              <button
                key={target}
                type="button"
                onClick={() => setDialog({ kind: 'status', target })}
                className={target === 'completed' || target === 'scheduled' ? primaryButtonClassName : secondaryButtonClassName}
              >
                {t(`training.statusAction.${target}`)}
              </button>
            ))}
          </div>
        ) : null}
      </header>

      <Details event={data} />

      <section aria-labelledby="sessions-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="sessions-heading" className="text-lg font-semibold text-slate-900">
            {t('training.sessions.title')}
          </h2>
          {sessionsEditable ? (
            <button type="button" onClick={() => setDialog({ kind: 'session', session: null })} className={secondaryButtonClassName}>
              <Plus aria-hidden="true" className="size-4" />
              {t('training.sessions.add')}
            </button>
          ) : null}
        </div>
        <Sessions event={data} editable={sessionsEditable} onEdit={(s) => setDialog({ kind: 'session', session: s })} onCancel={(s) => setDialog({ kind: 'cancelSession', session: s })} />
      </section>

      <Participants
        event={data}
        canManage={canManage}
        onAdd={() => setDialog({ kind: 'add' })}
        onRecord={(p) => setDialog({ kind: 'record', participation: p })}
        onWithdraw={(p) => setDialog({ kind: 'withdraw', participation: p })}
      />

      {dialog?.kind === 'edit' ? <EventFormDialog event={data} onClose={close} onSaved={close} /> : null}
      {dialog?.kind === 'status' ? <StatusDialog event={data} target={dialog.target} onClose={close} /> : null}
      {dialog?.kind === 'session' ? <SessionDialog event={data} session={dialog.session} onClose={close} /> : null}
      {dialog?.kind === 'cancelSession' ? <CancelSessionDialog event={data} session={dialog.session} onClose={close} /> : null}
      {dialog?.kind === 'add' ? <AddParticipantsDialog event={data} onClose={close} /> : null}
      {dialog?.kind === 'record' ? <ParticipationDialog event={data} participation={dialog.participation} onClose={close} /> : null}
      {dialog?.kind === 'withdraw' ? <WithdrawDialog event={data} participation={dialog.participation} onClose={close} /> : null}
    </div>
  )
}

function Details({ event }: { event: TrainingEvent }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const when = useWhenText()
  const duration = useDurationText()
  const mode = useDeliveryModeLabel()
  const d = (value: string | null) => (value ? formatDate(value, language) : '—')
  const num = (value: number | null) => (value === null ? '—' : new Intl.NumberFormat(language).format(value))
  const trainer =
    event.trainer_employee?.name ?? event.trainer_name ?? '—'
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <section aria-labelledby="planned-heading" className={`${cardClassName} space-y-3`}>
        <h2 id="planned-heading" className="font-semibold text-slate-900">{t('training.event.planned')}</h2>
        <dl className="grid gap-3">
          <Field label={t('training.fields.when')}>
            {when({
              start: event.planned_start_date,
              end: event.planned_end_date,
              planned_month: event.planned_month,
              planned_start_date: event.planned_start_date,
            })}
          </Field>
          <Field label={t('training.fields.durationMinutes')}>{duration(event.planned_duration_minutes)}</Field>
          <Field label={t('training.fields.plannedCount')}>{num(event.planned_participant_count)}</Field>
          <Field label={t('training.fields.plannedManhours')}>{num(event.planned_manhours)}</Field>
        </dl>
      </section>
      <section aria-labelledby="actual-heading" className={`${cardClassName} space-y-3`}>
        <h2 id="actual-heading" className="font-semibold text-slate-900">{t('training.event.actual')}</h2>
        <dl className="grid gap-3">
          <Field label={t('training.fields.actualStart')}>{d(event.actual_start_date)}</Field>
          <Field label={t('training.fields.actualEnd')}>{d(event.actual_end_date)}</Field>
          <Field label={t('training.fields.reportedCount')}>{num(event.reported_attendance_count)}</Field>
          <Field label={t('training.fields.reportedManhours')}>{num(event.reported_manhours)}</Field>
          <Field label={t('training.event.recorded')}>
            {t('training.register.counts', {
              participants: event.counts.participants,
              attended: event.counts.attended,
              completed: event.counts.completed,
            })}
          </Field>
        </dl>
        {event.actual_start_date === null ? (
          <p className="text-xs text-slate-500">{t('training.event.noActual')}</p>
        ) : null}
      </section>
      <section aria-labelledby="general-heading" className={`${cardClassName} space-y-3`}>
        <h2 id="general-heading" className="font-semibold text-slate-900">{t('training.event.general')}</h2>
        <dl className="grid gap-3">
          <Field label={t('training.fields.programme')}>{event.programme ? `${event.programme.name} (${event.programme.code})` : '—'}</Field>
          <Field label={t('training.fields.deliveryMode')}>{mode(event.delivery_mode)}</Field>
          <Field label={t('training.fields.orgUnit')}>{event.org_unit?.name ?? '—'}</Field>
          <Field label={t('training.fields.location')}>{event.location?.name ?? '—'}</Field>
          <Field label={t('training.fields.venue')}>{event.venue ?? '—'}</Field>
          {event.online_join_url ? (
            <Field label={t('training.fields.onlineLink')}>
              <a href={event.online_join_url} target="_blank" rel="noreferrer noopener" className="text-brand-700 underline">
                {t('training.event.join')}
              </a>
            </Field>
          ) : null}
          <Field label={t('training.fields.trainer')}>
            {trainer}
            {event.trainer_type ? ` (${t(`training.trainer.${event.trainer_type === 'external' ? 'external' : 'internal'}`)})` : ''}
          </Field>
          <Field label={t('training.fields.provider')}>{event.provider_name ?? '—'}</Field>
          <Field label={t('training.fields.capacity')}>{num(event.capacity)}</Field>
          <Field label={t('training.fields.targetAudience')}>{event.target_audience ?? '—'}</Field>
          <Field label={t('training.fields.calendarLabel')}>{event.calendar_label ?? '—'}</Field>
          <Field label={t('training.fields.source')}>{event.source === 'import' ? t('training.source.import') : t('training.source.manual')}</Field>
        </dl>
      </section>
      {event.description || event.instructions ? (
        <section className={`${cardClassName} space-y-2 lg:col-span-3`}>
          {event.description ? <Field label={t('training.fields.description')}>{event.description}</Field> : null}
          {event.instructions ? <Field label={t('training.fields.instructions')}>{event.instructions}</Field> : null}
        </section>
      ) : null}
      <p className="text-xs text-slate-500 lg:col-span-3">{t('training.event.manhoursNote')}</p>
    </div>
  )
}

function Sessions({
  event,
  editable,
  onEdit,
  onCancel,
}: {
  event: TrainingEvent
  editable: boolean
  onEdit: (session: TrainingSession) => void
  onCancel: (session: TrainingSession) => void
}) {
  const { t, i18n } = useTranslation()
  if (event.sessions.length === 0) return <EmptyState title={t('training.sessions.empty')} />
  return (
    <ul className="space-y-2">
      {event.sessions.map((session) => (
        <li key={session.public_id} className={`${cardClassName} flex flex-wrap items-center justify-between gap-3`}>
          <div className="min-w-0 text-sm">
            <p className={`font-medium ${session.status === 'cancelled' ? 'text-slate-500 line-through' : 'text-slate-900'}`}>
              {formatDateTime(session.starts_at, i18n.resolvedLanguage)} – {formatDateTime(session.ends_at, i18n.resolvedLanguage, { timeStyle: 'short' })}
            </p>
            <p className="text-slate-600">
              {[session.venue, session.online_join_url ? t('training.calendar.online') : null, session.notes].filter(Boolean).join(' · ') || '—'}
            </p>
            {session.status === 'cancelled' ? <p className="text-xs font-medium text-red-700">{t('training.sessions.cancelled')}</p> : null}
          </div>
          {editable && session.status !== 'cancelled' ? (
            <div className="flex gap-2">
              <button type="button" onClick={() => onEdit(session)} className={secondaryButtonClassName}>
                {t('training.sessions.edit')}
              </button>
              <button type="button" onClick={() => onCancel(session)} className={secondaryButtonClassName}>
                {t('training.sessions.cancel')}
              </button>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function Participants({
  event,
  canManage,
  onAdd,
  onRecord,
  onWithdraw,
}: {
  event: TrainingEvent
  canManage: boolean
  onAdd: () => void
  onRecord: (p: Participation) => void
  onWithdraw: (p: Participation) => void
}) {
  const { t } = useTranslation()
  const participants = useParticipants(event.public_id)
  return (
    <section aria-labelledby="participants-heading" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="participants-heading" className="text-lg font-semibold text-slate-900">
          {t('training.participants.title')}
        </h2>
        {canManage && event.status !== 'cancelled' ? (
          <button type="button" onClick={onAdd} className={secondaryButtonClassName}>
            <UserPlus aria-hidden="true" className="size-4" />
            {t('training.participants.addTitle')}
          </button>
        ) : null}
      </div>
      <p className="text-sm text-slate-600">{t('training.participants.evidenceNote')}</p>
      {participants.isPending ? (
        <LoadingState />
      ) : participants.isError ? (
        <FeatureError error={participants.error} title={t('training.participants.loadError')} onRetry={() => void participants.refetch()} />
      ) : participants.data.length === 0 ? (
        <EmptyState title={t('training.participants.empty')} />
      ) : (
        <div className={tableWrapClassName}>
          <table className={tableClassName}>
            <caption className="sr-only">{t('training.participants.caption', { title: event.title })}</caption>
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className={thClassName}>{t('training.fields.employee')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.nomination')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.attendance')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.completion')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.assessmentResult')}</th>
                <th scope="col" className={thClassName}>{t('training.fields.certificate')}</th>
                {canManage ? <th scope="col" className={thClassName}><span className="sr-only">{t('training.participants.actions')}</span></th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {participants.data.map((p) => (
                <tr key={p.public_id}>
                  <td className={tdClassName}>
                    {p.employee.name}
                    <p className="text-xs text-slate-500">{p.employee.employee_code}</p>
                  </td>
                  <td className={tdClassName}><NominationBadge value={p.nomination_status} /></td>
                  <td className={tdClassName}>
                    <AttendanceBadge value={p.attendance_status} />
                    {p.attended_minutes !== null ? <p className="text-xs text-slate-500">{t('training.durationMinutes', { minutes: p.attended_minutes })}</p> : null}
                  </td>
                  <td className={tdClassName}><CompletionBadge value={p.completion_status} /></td>
                  <td className={tdClassName}>{p.assessment_result ?? '—'}</td>
                  <td className={tdClassName}>{p.certificate_number ?? '—'}</td>
                  {canManage ? (
                    <td className={`${tdClassName} whitespace-nowrap`}>
                      {p.nomination_status !== 'withdrawn' ? (
                        <div className="flex gap-2">
                          <button type="button" onClick={() => onRecord(p)} className="text-sm font-medium text-brand-700 hover:underline">
                            {t('training.participants.record', { name: p.employee.name })}
                          </button>
                          <button type="button" onClick={() => onWithdraw(p)} className="text-sm text-slate-600 hover:underline">
                            {t('training.participants.withdrawShort')}
                          </button>
                        </div>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
