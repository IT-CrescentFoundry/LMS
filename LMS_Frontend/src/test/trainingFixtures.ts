/**
 * Synthetic training, notification and competency data for frontend tests.
 * Every name, code and identifier is invented.
 */

import { PERMISSIONS } from '../features/auth/permissions'
import { HR_ADMIN, makeUser } from './renderApp'

export const TRAINING_ADMIN = makeUser({
  ...HR_ADMIN,
  public_id: '01900000-0000-7000-8000-0000000000a1',
  login_id: 'test.training.admin',
  display_name: 'Test Training Admin',
  permissions: [
    ...HR_ADMIN.permissions,
    PERMISSIONS.TRAINING_RECORDS_VIEW,
    PERMISSIONS.COMPETENCY_VIEW,
    PERMISSIONS.COMPETENCY_MANAGE,
    PERMISSIONS.COMPETENCY_ASSESS,
    PERMISSIONS.IMPORTS_ORGANISATION_RUN,
    PERMISSIONS.IMPORTS_ORGANISATION_COMMIT,
  ],
})

export const EMP_A = { public_id: 'emp-a', employee_code: 'SYN-001', name: 'Synthetic Person A' }
export const EMP_B = { public_id: 'emp-b', employee_code: 'SYN-002', name: 'Synthetic Person B' }

export function session(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'session-1',
    starts_at: '2026-12-03T04:30:00Z',
    ends_at: '2026-12-03T06:30:00Z',
    venue: 'Training Room 1',
    online_join_url: null,
    status: 'scheduled',
    notes: null,
    version: 1,
    ...overrides,
  }
}

export function trainingEvent(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'event-1',
    code: 'TE-SYN-1',
    title: 'Synthetic fire safety basics',
    description: null,
    status: 'scheduled',
    status_reason: null,
    timeframe: 'upcoming',
    delivery_mode: 'classroom',
    programme: null,
    category: null,
    org_unit: null,
    location: null,
    calendar_label: 'Synthetic calendar 2026-27',
    planned_month: null,
    planned_start_date: '2026-12-03',
    planned_end_date: null,
    actual_start_date: null,
    actual_end_date: null,
    planned_duration_minutes: 120,
    venue: 'Training Room 1',
    online_join_url: null,
    trainer_type: 'external',
    trainer_employee: null,
    trainer_name: 'Synthetic Trainer',
    provider_name: null,
    capacity: 20,
    planned_participant_count: 12,
    reported_attendance_count: null,
    planned_manhours: 24,
    reported_manhours: null,
    target_audience: null,
    instructions: null,
    source: 'manual',
    published_at: '2026-11-20T10:00:00Z',
    counts: { participants: 1, attended: 0, completed: 0 },
    sessions: [session()],
    version: 3,
    ...overrides,
  }
}

export function eventPage(items: unknown[], total = items.length) {
  return { items, total, limit: 25, offset: 0 }
}

export const SUMMARY = {
  scope: 'global',
  events_total: 4,
  events_planned: 1,
  events_scheduled: 2,
  events_completed: 1,
  events_cancelled: 0,
  events_postponed: 0,
  events_upcoming: 2,
  participations: 7,
  attendance_recorded_present: 3,
  completions_recorded: 2,
}

export function participation(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'part-1',
    employee: EMP_A,
    event: {
      public_id: 'event-1',
      code: 'TE-SYN-1',
      title: 'Synthetic fire safety basics',
      status: 'scheduled',
      timeframe: 'upcoming',
      start: '2026-12-03',
      end: '2026-12-03',
    },
    nomination_status: 'nominated',
    attendance_status: null,
    attended_minutes: null,
    completion_status: null,
    assessment_result: null,
    certificate_number: null,
    remarks: null,
    source: 'manual',
    attendance_recorded_at: null,
    completion_recorded_at: null,
    version: 1,
    ...overrides,
  }
}

export function calendarItem(overrides: Record<string, unknown> = {}) {
  return {
    event: participation().event,
    session: session(),
    all_day: false,
    starts_at: '2026-12-03T04:30:00Z',
    ends_at: '2026-12-03T06:30:00Z',
    start_date: '2026-12-03',
    end_date: '2026-12-03',
    month_only: false,
    venue: 'Training Room 1',
    online: false,
    delivery_mode: 'classroom',
    org_unit: null,
    location: null,
    my_status: null,
    ...overrides,
  }
}

export function notification(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'note-1',
    notification_type: 'training.reminder',
    title: 'Reminder: Synthetic fire safety basics',
    body: "'Synthetic fire safety basics' starts 2026-12-03 04:30 UTC at Training Room 1.",
    link_path: '/training/events/event-1',
    created_at: '2026-12-02T04:30:00Z',
    read_at: null,
    ...overrides,
  }
}

export const PREFERENCES = {
  preferences: {
    'training.nominated': true,
    'training.schedule_published': true,
    'training.schedule_changed': true,
    'training.cancelled': true,
    'training.reminder': true,
    'training.completed': true,
    'training.certificate_recorded': true,
  },
  mandatory: ['training.cancelled', 'training.schedule_changed'],
}

export const CHANNELS = {
  channels: [
    { code: 'in_app', name: 'Portal notification centre', connected: true, detail: 'x' },
    { code: 'outlook', name: 'Outlook calendar', connected: false, detail: 'x' },
    { code: 'teams', name: 'Microsoft Teams', connected: false, detail: 'x' },
  ],
  reminder_offsets_days: [1, 7],
}

const level = (rank: number, label: string) => ({
  public_id: `lvl-${rank}`,
  rank,
  code: `L${rank}`,
  label,
  numeric_value: rank,
  description: null,
})

export const SCALE = {
  public_id: 'scale-1',
  code: 'SYN_SCALE_1_5',
  name: 'Synthetic scale (1-5)',
  description: null,
  gap_method: 'ordinal',
  source_note: 'Synthetic test scale',
  competent_rank: 3,
  plan_gap_steps: 2,
  is_active: true,
  levels: [level(1, 'Beginner'), level(2, 'Supervised'), level(3, 'Independent'), level(4, 'Expert'), level(5, 'Trainer')],
  version: 1,
}

export const MATRIX = {
  public_id: 'matrix-1',
  code: 'MX-SYN',
  name: 'Synthetic moulding matrix',
  description: null,
  org_unit: null,
  location: null,
  designation: null,
  functional_role: null,
  scale: SCALE,
  risk_medium_margin: 1,
  is_active: true,
  member_count: 2,
  items: [
    {
      competency: { public_id: 'comp-1', code: 'SYN-01', name: 'Synthetic core making' },
      category: 'Moulding',
      group_label: 'Moulding',
      display_order: 0,
      required_level: level(4, 'Expert'),
      required_headcount: 2,
    },
    {
      competency: { public_id: 'comp-2', code: 'SYN-02', name: 'Synthetic sand testing' },
      category: 'Moulding',
      group_label: 'Moulding',
      display_order: 1,
      required_level: null,
      required_headcount: null,
    },
  ],
  version: 2,
}

export const GRID = {
  matrix: MATRIX,
  scope: 'global',
  rows: [
    {
      employee: EMP_A,
      gaps: 1,
      cells: [
        {
          competency_id: 'comp-1',
          required_level: level(4, 'Expert'),
          assessed_level: level(2, 'Supervised'),
          assessed_on: '2026-11-01',
          gap: { status: 'below', gap_steps: 2, gap_value: null },
          needs_plan: true,
        },
        {
          competency_id: 'comp-2',
          required_level: null,
          assessed_level: null,
          assessed_on: null,
          gap: { status: 'requirement_pending', gap_steps: null, gap_value: null },
          needs_plan: false,
        },
      ],
    },
    {
      employee: EMP_B,
      gaps: 0,
      cells: [
        {
          competency_id: 'comp-1',
          required_level: level(4, 'Expert'),
          assessed_level: level(4, 'Expert'),
          assessed_on: '2026-11-01',
          gap: { status: 'met', gap_steps: 0, gap_value: null },
          needs_plan: false,
        },
        {
          competency_id: 'comp-2',
          required_level: null,
          assessed_level: null,
          assessed_on: null,
          gap: { status: 'not_assessed', gap_steps: null, gap_value: null },
          needs_plan: false,
        },
      ],
    },
  ],
  summary: { below: 1, met: 1, exceeds: 0, not_assessed: 1, requirement_pending: 1, needs_plan: 1, risk_high: 1, risk_medium: 0, risk_low: 0 },
  item_stats: [
    { competency_id: 'comp-1', counts_by_rank: { '1': 0, '2': 1, '3': 0, '4': 1, '5': 0 }, not_assessed: 0, skilled: 1, required_headcount: 2, risk: 'high' },
    { competency_id: 'comp-2', counts_by_rank: { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0 }, not_assessed: 2, skilled: 0, required_headcount: null, risk: null },
  ],
}

export function competency(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'comp-1',
    code: 'SYN-01',
    name: 'Synthetic core making',
    category: 'Operation',
    sub_category: 'Moulding',
    description: 'Synthetic description',
    assessment_criteria: null,
    applicability: null,
    scale: { public_id: 'scale-1', code: 'SYN_SCALE_1_5', name: 'Synthetic scale (1-5)' },
    owner_org_unit: null,
    source_ref: null,
    is_active: true,
    status: 'draft',
    approved_at: null,
    band_requirements: [],
    version: 1,
    ...overrides,
  }
}

export function schemaPending() {
  return {
    error: {
      code: 'schema_migration_pending',
      message: 'This feature needs database migration 0011.',
      request_id: 'req-test-1',
    },
  }
}
