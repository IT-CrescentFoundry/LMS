/**
 * Training register and calendar API (`/training`, migration 0011).
 *
 * Reads need one of training.records.view / team.learning.view / learning.own.view /
 * training_events.manage; the server narrows every list to the caller's scope.
 * Writes need training_events.manage, the session cookie and the CSRF token. Until the
 * migration is applied the server answers 503 `schema_migration_pending`.
 */

import { apiRequest, buildQuery, type HttpMethod } from '../lib/apiClient'
import {
  expectArray,
  expectBoolean,
  expectDateString,
  expectInteger,
  expectNullableDateString,
  expectNullableInteger,
  expectNullableIsoDate,
  expectNullableNumber,
  expectNullableString,
  expectOneOf,
  expectRecord,
  expectString,
  expectStringArray,
} from '../lib/parse'
import type { Ref } from '../types/organisation'
import {
  ATTENDANCE_STATUSES,
  COMPLETION_STATUSES,
  EVENT_STATUSES,
  NOMINATION_STATUSES,
  RECORD_SCOPES,
  TIMEFRAMES,
  type CalendarData,
  type CalendarFilters,
  type CalendarItem,
  type EmployeeRef,
  type EventBody,
  type EventBrief,
  type EventFilters,
  type OffsetPage,
  type ParticipantsAddResult,
  type Participation,
  type ParticipationFilters,
  type Programme,
  type RegisterSummary,
  type TrainingEvent,
  type TrainingSession,
} from '../types/training'

const TR = '/training'
export const EVENT_PAGE_SIZE = 25

// ------------------------------------------------------------------------ parsers

export function parseRef(data: unknown): Ref | null {
  if (data === null || data === undefined) return null
  const record = expectRecord(data, 'ref')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
  }
}

export function parseEmployeeRef(data: unknown): EmployeeRef | null {
  if (data === null || data === undefined) return null
  const record = expectRecord(data, 'employee')
  return {
    public_id: expectString(record, 'public_id'),
    employee_code: expectString(record, 'employee_code'),
    name: expectString(record, 'name'),
  }
}

function requiredEmployee(data: unknown): EmployeeRef {
  const employee = parseEmployeeRef(data)
  if (employee === null) throw new TypeError('employee: expected an object')
  return employee
}

export function parseOffsetPage<T>(parseItem: (data: unknown) => T): (data: unknown) => OffsetPage<T> {
  return (data) => {
    const record = expectRecord(data, 'page')
    return {
      items: expectArray(record, 'items').map(parseItem),
      total: expectInteger(record, 'total'),
      limit: expectInteger(record, 'limit'),
      offset: expectInteger(record, 'offset'),
    }
  }
}

export function parseProgramme(data: unknown): Programme {
  const r = expectRecord(data, 'programme')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    title: expectString(r, 'title'),
    category: expectNullableString(r, 'category'),
    description: expectNullableString(r, 'description'),
    objectives: expectNullableString(r, 'objectives'),
    target_audience: expectNullableString(r, 'target_audience'),
    default_delivery_mode: expectNullableString(r, 'default_delivery_mode'),
    standard_duration_minutes: expectNullableInteger(r, 'standard_duration_minutes'),
    is_active: expectBoolean(r, 'is_active'),
    version: expectInteger(r, 'version'),
  }
}

export function parseSession(data: unknown): TrainingSession {
  const r = expectRecord(data, 'session')
  return {
    public_id: expectString(r, 'public_id'),
    starts_at: expectDateString(r, 'starts_at'),
    ends_at: expectDateString(r, 'ends_at'),
    venue: expectNullableString(r, 'venue'),
    online_join_url: expectNullableString(r, 'online_join_url'),
    status: expectString(r, 'status'),
    notes: expectNullableString(r, 'notes'),
    version: expectInteger(r, 'version'),
  }
}

export function parseEvent(data: unknown): TrainingEvent {
  const r = expectRecord(data, 'event')
  const counts = expectRecord(r.counts, 'counts')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    title: expectString(r, 'title'),
    description: expectNullableString(r, 'description'),
    status: expectOneOf(r, 'status', EVENT_STATUSES),
    status_reason: expectNullableString(r, 'status_reason'),
    timeframe: expectOneOf(r, 'timeframe', TIMEFRAMES),
    delivery_mode: expectNullableString(r, 'delivery_mode'),
    programme: parseRef(r.programme),
    category: expectNullableString(r, 'category'),
    org_unit: parseRef(r.org_unit),
    location: parseRef(r.location),
    calendar_label: expectNullableString(r, 'calendar_label'),
    planned_month: expectNullableIsoDate(r, 'planned_month'),
    planned_start_date: expectNullableIsoDate(r, 'planned_start_date'),
    planned_end_date: expectNullableIsoDate(r, 'planned_end_date'),
    actual_start_date: expectNullableIsoDate(r, 'actual_start_date'),
    actual_end_date: expectNullableIsoDate(r, 'actual_end_date'),
    planned_duration_minutes: expectNullableInteger(r, 'planned_duration_minutes'),
    venue: expectNullableString(r, 'venue'),
    online_join_url: expectNullableString(r, 'online_join_url'),
    trainer_type: expectNullableString(r, 'trainer_type'),
    trainer_employee: parseEmployeeRef(r.trainer_employee),
    trainer_name: expectNullableString(r, 'trainer_name'),
    provider_name: expectNullableString(r, 'provider_name'),
    capacity: expectNullableInteger(r, 'capacity'),
    planned_participant_count: expectNullableInteger(r, 'planned_participant_count'),
    reported_attendance_count: expectNullableInteger(r, 'reported_attendance_count'),
    planned_manhours: expectNullableNumber(r, 'planned_manhours'),
    reported_manhours: expectNullableNumber(r, 'reported_manhours'),
    target_audience: expectNullableString(r, 'target_audience'),
    instructions: expectNullableString(r, 'instructions'),
    source: expectString(r, 'source'),
    published_at: expectNullableDateString(r, 'published_at'),
    counts: {
      participants: expectInteger(counts, 'participants'),
      attended: expectInteger(counts, 'attended'),
      completed: expectInteger(counts, 'completed'),
    },
    sessions: expectArray(r, 'sessions').map(parseSession),
    version: expectInteger(r, 'version'),
  }
}

export function parseSummary(data: unknown): RegisterSummary {
  const r = expectRecord(data, 'summary')
  return {
    scope: expectOneOf(r, 'scope', RECORD_SCOPES),
    events_total: expectInteger(r, 'events_total'),
    events_planned: expectInteger(r, 'events_planned'),
    events_scheduled: expectInteger(r, 'events_scheduled'),
    events_completed: expectInteger(r, 'events_completed'),
    events_cancelled: expectInteger(r, 'events_cancelled'),
    events_postponed: expectInteger(r, 'events_postponed'),
    events_upcoming: expectInteger(r, 'events_upcoming'),
    participations: expectInteger(r, 'participations'),
    attendance_recorded_present: expectInteger(r, 'attendance_recorded_present'),
    completions_recorded: expectInteger(r, 'completions_recorded'),
  }
}

export function parseEventBrief(data: unknown): EventBrief {
  const r = expectRecord(data, 'event')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    title: expectString(r, 'title'),
    status: expectOneOf(r, 'status', EVENT_STATUSES),
    timeframe: expectOneOf(r, 'timeframe', TIMEFRAMES),
    start: expectNullableIsoDate(r, 'start'),
    end: expectNullableIsoDate(r, 'end'),
  }
}

function nullableOneOf<T extends string>(r: Record<string, unknown>, key: string, allowed: readonly T[]): T | null {
  return r[key] === null || r[key] === undefined ? null : expectOneOf(r, key, allowed)
}

export function parseParticipation(data: unknown): Participation {
  const r = expectRecord(data, 'participation')
  return {
    public_id: expectString(r, 'public_id'),
    employee: requiredEmployee(r.employee),
    event: parseEventBrief(r.event),
    nomination_status: expectOneOf(r, 'nomination_status', NOMINATION_STATUSES),
    attendance_status: nullableOneOf(r, 'attendance_status', ATTENDANCE_STATUSES),
    attended_minutes: expectNullableInteger(r, 'attended_minutes'),
    completion_status: nullableOneOf(r, 'completion_status', COMPLETION_STATUSES),
    assessment_result: expectNullableString(r, 'assessment_result'),
    certificate_number: expectNullableString(r, 'certificate_number'),
    remarks: expectNullableString(r, 'remarks'),
    source: expectString(r, 'source'),
    attendance_recorded_at: expectNullableDateString(r, 'attendance_recorded_at'),
    completion_recorded_at: expectNullableDateString(r, 'completion_recorded_at'),
    version: expectInteger(r, 'version'),
  }
}

function parseAddResult(data: unknown): ParticipantsAddResult {
  const r = expectRecord(data, 'result')
  return {
    added: expectInteger(r, 'added'),
    already_participating: expectStringArray(r, 'already_participating'),
    employment_status_not_recorded: expectStringArray(r, 'employment_status_not_recorded'),
  }
}

export function parseCalendarItem(data: unknown): CalendarItem {
  const r = expectRecord(data, 'item')
  return {
    event: parseEventBrief(r.event),
    session: r.session === null || r.session === undefined ? null : parseSession(r.session),
    all_day: expectBoolean(r, 'all_day'),
    starts_at: expectNullableDateString(r, 'starts_at'),
    ends_at: expectNullableDateString(r, 'ends_at'),
    start_date: expectNullableIsoDate(r, 'start_date'),
    end_date: expectNullableIsoDate(r, 'end_date'),
    month_only: expectBoolean(r, 'month_only'),
    venue: expectNullableString(r, 'venue'),
    online: expectBoolean(r, 'online'),
    delivery_mode: expectNullableString(r, 'delivery_mode'),
    org_unit: parseRef(r.org_unit),
    location: parseRef(r.location),
    my_status: expectNullableString(r, 'my_status'),
  }
}

export function parseCalendar(data: unknown): CalendarData {
  const r = expectRecord(data, 'calendar')
  return {
    scope: expectOneOf(r, 'scope', RECORD_SCOPES),
    start: expectString(r, 'start'),
    end: expectString(r, 'end'),
    items: expectArray(r, 'items').map(parseCalendarItem),
  }
}

function parseStringList(data: unknown): string[] {
  if (!Array.isArray(data) || !data.every((item) => typeof item === 'string')) {
    throw new TypeError('expected a list of strings')
  }
  return [...data]
}

function send<T>(path: string, method: HttpMethod, body: unknown, parse: (data: unknown) => T): Promise<T> {
  return apiRequest(`${TR}${path}`, { method, body, parse })
}

// -------------------------------------------------------------------------- service

export const trainingService = {
  summary(filters: { unit?: string; location?: string }, signal?: AbortSignal): Promise<RegisterSummary> {
    return apiRequest(`${TR}/summary${buildQuery({ unit: filters.unit, location: filters.location })}`, {
      parse: parseSummary,
      signal,
    })
  },

  listEvents(filters: EventFilters, offset: number, signal?: AbortSignal, limit = EVENT_PAGE_SIZE) {
    const query = buildQuery({
      q: filters.q,
      status: filters.status,
      timeframe: filters.timeframe,
      unit: filters.unit,
      location: filters.location,
      category: filters.category,
      calendar_label: filters.calendar_label,
      date_from: filters.date_from,
      date_to: filters.date_to,
      limit,
      offset,
    })
    return apiRequest(`${TR}/events${query}`, { parse: parseOffsetPage(parseEvent), signal })
  },

  calendarLabels(signal?: AbortSignal): Promise<string[]> {
    return apiRequest(`${TR}/calendar-labels`, { parse: parseStringList, signal })
  },

  getEvent(id: string, signal?: AbortSignal): Promise<TrainingEvent> {
    return apiRequest(`${TR}/events/${encodeURIComponent(id)}`, { parse: parseEvent, signal })
  },

  createEvent(body: EventBody): Promise<TrainingEvent> {
    return send('/events', 'POST', body, parseEvent)
  },

  updateEvent(id: string, body: EventBody & { version: number }): Promise<TrainingEvent> {
    return send(`/events/${encodeURIComponent(id)}`, 'PATCH', body, parseEvent)
  },

  changeStatus(
    id: string,
    body: {
      version: number
      status: string
      reason?: string | null
      actual_start_date?: string | null
      actual_end_date?: string | null
    },
  ): Promise<TrainingEvent> {
    return send(`/events/${encodeURIComponent(id)}/status`, 'POST', body, parseEvent)
  },

  addSession(id: string, body: Record<string, string | null>): Promise<TrainingEvent> {
    return send(`/events/${encodeURIComponent(id)}/sessions`, 'POST', body, parseEvent)
  },

  updateSession(id: string, sessionId: string, body: Record<string, string | number | null>): Promise<TrainingEvent> {
    return send(
      `/events/${encodeURIComponent(id)}/sessions/${encodeURIComponent(sessionId)}`,
      'PATCH',
      body,
      parseEvent,
    )
  },

  participants(id: string, signal?: AbortSignal): Promise<Participation[]> {
    return apiRequest(`${TR}/events/${encodeURIComponent(id)}/participants`, {
      parse: (data) => {
        if (!Array.isArray(data)) throw new TypeError('expected a list')
        return data.map(parseParticipation)
      },
      signal,
    })
  },

  addParticipants(
    id: string,
    body: { employees: string[]; nomination_status: 'nominated' | 'confirmed' },
  ): Promise<ParticipantsAddResult> {
    return send(`/events/${encodeURIComponent(id)}/participants`, 'POST', body, parseAddResult)
  },

  updateParticipation(
    id: string,
    participationId: string,
    body: Record<string, string | number | null>,
  ): Promise<Participation> {
    return send(
      `/events/${encodeURIComponent(id)}/participants/${encodeURIComponent(participationId)}`,
      'PATCH',
      body,
      parseParticipation,
    )
  },

  listParticipations(filters: ParticipationFilters, offset: number, signal?: AbortSignal, limit = 50) {
    const query = buildQuery({
      q: filters.q,
      unit: filters.unit,
      designation: filters.designation,
      attendance: filters.attendance,
      completion: filters.completion,
      employee: filters.employee,
      mine: filters.mine ? true : undefined,
      limit,
      offset,
    })
    return apiRequest(`${TR}/participations${query}`, { parse: parseOffsetPage(parseParticipation), signal })
  },

  calendar(filters: CalendarFilters, signal?: AbortSignal): Promise<CalendarData> {
    const query = buildQuery({
      start: filters.start,
      end: filters.end,
      mine: filters.mine ? true : undefined,
      unit: filters.unit,
      location: filters.location,
      status: filters.status,
      calendar_label: filters.calendar_label,
    })
    return apiRequest(`${TR}/calendar${query}`, { parse: parseCalendar, signal })
  },

  listProgrammes(
    filters: { q?: string; category?: string; include_inactive?: boolean },
    signal?: AbortSignal,
  ): Promise<Programme[]> {
    const query = buildQuery({
      q: filters.q,
      category: filters.category,
      include_inactive: filters.include_inactive ? true : undefined,
    })
    return apiRequest(`${TR}/programmes${query}`, {
      parse: (data) => {
        if (!Array.isArray(data)) throw new TypeError('expected a list')
        return data.map(parseProgramme)
      },
      signal,
    })
  },

  createProgramme(body: EventBody): Promise<Programme> {
    return send('/programmes', 'POST', body, parseProgramme)
  },

  updateProgramme(id: string, body: Record<string, string | number | boolean | null>): Promise<Programme> {
    return send(`/programmes/${encodeURIComponent(id)}`, 'PATCH', body, parseProgramme)
  },
}
