/**
 * Training register, calendar and notification types (first release, migration 0011).
 * Mirrors LMS_Backend/app/schemas/training.py.
 */

import type { Ref } from './organisation'

export const DELIVERY_MODES = ['classroom', 'online', 'hybrid', 'ojt'] as const
export type DeliveryMode = (typeof DELIVERY_MODES)[number]

export const EVENT_STATUSES = ['planned', 'scheduled', 'completed', 'postponed', 'cancelled'] as const
export type EventStatus = (typeof EVENT_STATUSES)[number]

export const TIMEFRAMES = ['past', 'ongoing', 'upcoming', 'unscheduled', 'cancelled'] as const
export type Timeframe = (typeof TIMEFRAMES)[number]

export const NOMINATION_STATUSES = ['nominated', 'confirmed', 'withdrawn'] as const
export type NominationStatus = (typeof NOMINATION_STATUSES)[number]

export const ATTENDANCE_STATUSES = ['present', 'partial', 'absent', 'excused'] as const
export type AttendanceStatus = (typeof ATTENDANCE_STATUSES)[number]

export const COMPLETION_STATUSES = ['completed', 'not_completed'] as const
export type CompletionStatus = (typeof COMPLETION_STATUSES)[number]

export const RECORD_SCOPES = ['global', 'team', 'own', 'none'] as const
export type RecordScope = (typeof RECORD_SCOPES)[number]

/** Allowed status changes (backend ALLOWED_TRANSITIONS). */
export const STATUS_TRANSITIONS: Record<EventStatus, readonly EventStatus[]> = {
  planned: ['scheduled', 'postponed', 'cancelled'],
  scheduled: ['planned', 'completed', 'postponed', 'cancelled'],
  postponed: ['planned', 'scheduled', 'cancelled'],
  completed: [],
  cancelled: [],
}

export interface OffsetPage<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface EmployeeRef {
  public_id: string
  employee_code: string
  name: string
}

export interface Programme {
  public_id: string
  code: string
  title: string
  category: string | null
  description: string | null
  objectives: string | null
  target_audience: string | null
  default_delivery_mode: string | null
  standard_duration_minutes: number | null
  is_active: boolean
  version: number
}

export interface TrainingSession {
  public_id: string
  starts_at: string
  ends_at: string
  venue: string | null
  online_join_url: string | null
  status: string
  notes: string | null
  version: number
}

export interface EventCounts {
  participants: number
  attended: number
  completed: number
}

export interface TrainingEvent {
  public_id: string
  code: string
  title: string
  description: string | null
  status: EventStatus
  status_reason: string | null
  timeframe: Timeframe
  delivery_mode: string | null
  programme: Ref | null
  category: string | null
  org_unit: Ref | null
  location: Ref | null
  calendar_label: string | null
  planned_month: string | null
  planned_start_date: string | null
  planned_end_date: string | null
  actual_start_date: string | null
  actual_end_date: string | null
  planned_duration_minutes: number | null
  venue: string | null
  online_join_url: string | null
  trainer_type: string | null
  trainer_employee: EmployeeRef | null
  trainer_name: string | null
  provider_name: string | null
  capacity: number | null
  planned_participant_count: number | null
  reported_attendance_count: number | null
  planned_manhours: number | null
  reported_manhours: number | null
  target_audience: string | null
  instructions: string | null
  source: string
  published_at: string | null
  counts: EventCounts
  sessions: TrainingSession[]
  version: number
}

export interface RegisterSummary {
  scope: RecordScope
  events_total: number
  events_planned: number
  events_scheduled: number
  events_completed: number
  events_cancelled: number
  events_postponed: number
  events_upcoming: number
  participations: number
  attendance_recorded_present: number
  completions_recorded: number
}

export interface EventBrief {
  public_id: string
  code: string
  title: string
  status: EventStatus
  timeframe: Timeframe
  start: string | null
  end: string | null
}

export interface Participation {
  public_id: string
  employee: EmployeeRef
  event: EventBrief
  nomination_status: NominationStatus
  attendance_status: AttendanceStatus | null
  attended_minutes: number | null
  completion_status: CompletionStatus | null
  assessment_result: string | null
  certificate_number: string | null
  remarks: string | null
  source: string
  attendance_recorded_at: string | null
  completion_recorded_at: string | null
  version: number
}

export interface ParticipantsAddResult {
  added: number
  already_participating: string[]
  employment_status_not_recorded: string[]
}

export interface CalendarItem {
  event: EventBrief
  session: TrainingSession | null
  all_day: boolean
  starts_at: string | null
  ends_at: string | null
  start_date: string | null
  end_date: string | null
  month_only: boolean
  venue: string | null
  online: boolean
  delivery_mode: string | null
  org_unit: Ref | null
  location: Ref | null
  my_status: string | null
}

export interface CalendarData {
  scope: RecordScope
  start: string
  end: string
  items: CalendarItem[]
}

export interface EventFilters {
  q?: string
  status?: EventStatus | ''
  timeframe?: Timeframe | ''
  unit?: string
  location?: string
  category?: string
  calendar_label?: string
  date_from?: string
  date_to?: string
}

export interface ParticipationFilters {
  q?: string
  unit?: string
  designation?: string
  attendance?: AttendanceStatus | 'not_recorded' | ''
  completion?: CompletionStatus | 'not_recorded' | ''
  employee?: string
  mine?: boolean
}

export interface CalendarFilters {
  start: string
  end: string
  mine?: boolean
  unit?: string
  location?: string
  status?: EventStatus | ''
  calendar_label?: string
}

/** Request bodies are plain objects; only the fields sent are changed (PATCH). */
export type EventBody = Record<string, string | number | null>

// --------------------------------------------------------------------- notifications

export interface AppNotification {
  public_id: string
  notification_type: string
  title: string
  body: string
  link_path: string | null
  created_at: string
  read_at: string | null
}

export interface NotificationList {
  items: AppNotification[]
  unread_count: number
}

export interface NotificationPreferences {
  preferences: Record<string, boolean>
  mandatory: string[]
}

export interface Channel {
  code: string
  name: string
  connected: boolean
  detail: string
}

export interface Channels {
  channels: Channel[]
  reminder_offsets_days: number[]
}
