/**
 * Synthetic employee data for the C3b tests. No real employee, code or name.
 * Shapes follow docs/architecture/API_REFERENCE.md section 9.
 */

import { BASELINE_NODES, DESIGNATION, LOCATION, page, ranked, ref, RESPONSIBILITY, ROLE, SUB_NODE, tree } from './orgFixtures'
import { reply, type MockRoute } from './renderApp'

const STAMP = { created_at: '2026-11-01T09:00:00Z', updated_at: '2026-11-02T09:00:00Z' }

export const OPERATION = ref('unit-ops', 'OPERATION', 'Operation')
export const MELT = ref('unit-melt', 'TEST_MELT', 'Test Melting')

export function employeeRef(id: string, code: string, name: string, status: string | null = 'active') {
  return { public_id: id, employee_code: code, full_name: name, employment_status: status }
}

export const MANAGER_REF = employeeRef('emp-mgr', 'T-MGR', 'Test Manager')

export function summary(id: string, code: string, name: string, overrides: Record<string, unknown> = {}) {
  return {
    public_id: id,
    employee_code: code,
    full_name: name,
    display_name: null,
    employment_status: 'active',
    as_of: '2026-11-14',
    primary_unit: MELT,
    path: [OPERATION],
    designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
    location: ref('loc-1', 'TEST_SITE', 'Test Site One'),
    line_manager: MANAGER_REF,
    has_active_account: true,
    ...overrides,
  }
}

export const ACTIVE = summary('emp-1', '00042', 'Test Person One')
export const UNKNOWN = summary('emp-2', 'T-0002', 'Test Person Two', {
  employment_status: null,
  primary_unit: null,
  path: [],
  designation: null,
  location: null,
  line_manager: null,
  has_active_account: false,
})
export const SEPARATED = summary('emp-3', 'T-0003', 'Test Person Three', {
  employment_status: 'separated',
  has_active_account: false,
})

export function employee(base: ReturnType<typeof summary> = ACTIVE, overrides: Record<string, unknown> = {}) {
  return {
    ...base,
    preferred_language: 'hi',
    work_email: 'person.one@example.test',
    date_of_joining: '2025-04-01',
    date_of_separation: null,
    external_ref: null,
    accounts: [{ public_id: 'acc-1', login_id: 'test.one', display_name: 'Test One', status: 'active' }],
    version: 3,
    ...STAMP,
    ...overrides,
  }
}

export const ASSIGNMENTS = [
  {
    public_id: 'asg-1',
    assignment_type: 'primary',
    org_unit: OPERATION,
    designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
    grade: null,
    job_level: null,
    location: null,
    effective_from: '2025-04-01',
    effective_to: '2026-07-01',
    source: 'manual',
    reason: 'Joined',
    version: 2,
    ...STAMP,
  },
  {
    public_id: 'asg-2',
    assignment_type: 'primary',
    org_unit: MELT,
    designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
    grade: ref('grade-1', 'TEST_G1', 'Test Grade One'),
    job_level: null,
    location: ref('loc-1', 'TEST_SITE', 'Test Site One'),
    effective_from: '2026-07-01',
    effective_to: null,
    source: 'manual',
    reason: 'Transfer',
    version: 1,
    ...STAMP,
  },
]

export const roleRecord = (id: string, role: ReturnType<typeof ref>, kind: string, reason: string | null) => ({
  public_id: id,
  functional_role: role,
  kind,
  effective_from: '2026-01-01',
  effective_to: null,
  reason,
  created_at: STAMP.created_at,
})

export const SAFETY = ref('role-safety', 'TEST_SAFETY', 'Test Safety Duty')
export const MELTING = ref('role-melt', 'TEST_MELTING', 'Test Melting Work')
export const AUDITOR = ref('role-audit', 'TEST_AUDIT', 'Test Internal Audit')

export const FUNCTIONAL_ROLES = {
  as_of: '2026-11-14',
  roles: [
    {
      functional_role: AUDITOR,
      effective: true,
      derived_from: [],
      manual: roleRecord('fr-2', AUDITOR, 'manual', 'Auditor'),
      exclusion: null,
    },
    {
      functional_role: MELTING,
      effective: true,
      derived_from: [
        {
          assignment: 'asg-2',
          assignment_type: 'primary',
          org_unit: MELT,
          designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
          mapping: 'map-1',
        },
      ],
      manual: null,
      exclusion: null,
    },
    {
      functional_role: SAFETY,
      effective: false,
      derived_from: [
        {
          assignment: 'asg-2',
          assignment_type: 'primary',
          org_unit: MELT,
          designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
          mapping: 'map-2',
        },
      ],
      manual: null,
      exclusion: roleRecord('fr-1', SAFETY, 'exclusion', 'Medical restriction'),
    },
  ],
  records: [
    roleRecord('fr-1', SAFETY, 'exclusion', 'Medical restriction'),
    roleRecord('fr-2', AUDITOR, 'manual', 'Auditor'),
  ],
}

export const RESPONSIBILITIES = [
  {
    public_id: 'resp-1',
    responsibility: ref('duty-1', 'TEST_WARDEN', 'Test Fire Warden'),
    context_unit: OPERATION,
    context_location: null,
    effective_from: '2026-02-01',
    effective_to: null,
    reason: null,
    created_at: STAMP.created_at,
  },
]

const LINE = ref('type-line', 'LINE_MANAGER', 'Line manager')
export const reportingRecord = (
  id: string,
  employeeBody: ReturnType<typeof employeeRef>,
  manager: ReturnType<typeof employeeRef>,
  from: string,
  to: string | null,
) => ({
  public_id: id,
  relationship_type: LINE,
  employee: employeeBody,
  manager,
  effective_from: from,
  effective_to: to,
  reason: null,
  created_at: STAMP.created_at,
})

export const ME = employeeRef('emp-1', '00042', 'Test Person One')
export const REPORTING = {
  as_of: '2026-11-14',
  managers: [reportingRecord('rep-2', ME, MANAGER_REF, '2026-07-01', null)],
  history: [
    reportingRecord('rep-1', ME, employeeRef('emp-old', 'T-OLD', 'Test Old Manager', 'separated'), '2025-04-01', '2026-07-01'),
    reportingRecord('rep-2', ME, MANAGER_REF, '2026-07-01', null),
  ],
  direct_reports: [
    reportingRecord('rep-3', employeeRef('emp-sub', 'T-SUB', 'Test Subordinate', null), ME, '2026-08-01', null),
  ],
}

export function auditEvent(id: string, type: string, metadata: Record<string, unknown>, at = '2026-11-10T08:00:00Z') {
  return {
    event_id: id,
    occurred_at: at,
    event_type: type,
    outcome: 'success',
    actor: { public_id: 'user-hr', login_id: 'hr.tester', display_name: 'HR Tester' },
    target_type: 'employee',
    target_id: 'emp-1',
    request_id: 'req-1',
    // The API never sends network details for employee views; null as in production.
    source_ip: null,
    user_agent: null,
    metadata,
  }
}

export const ACCOUNT = {
  accounts: [
    { public_id: 'acc-1', login_id: 'test.one', display_name: 'Test One', status: 'active' },
    { public_id: 'acc-0', login_id: 'test.one.old', display_name: 'Test One (old)', status: 'disabled' },
  ],
  flags: ['email_mismatch'],
  history: [
    auditEvent('ev-link', 'employee_account.linked', {
      employee_code: '00042',
      account: 'acc-1',
      login_id: 'test.one',
      account_status: 'active',
      reason: 'New login',
    }),
  ],
}

export const HISTORY_PAGE = {
  items: [
    auditEvent('ev-2', 'employee_assignment.changed', { employee_code: '00042', reason: 'Transfer' }),
    auditEvent('ev-1', 'employee.created', { employee_code: '00042', employment_status: 'active' }, '2025-04-01T08:00:00Z'),
  ],
  next_cursor: null,
}

/** Reference data used by the directory filters (organisation.view). */
function orgRoutes(): Record<string, MockRoute> {
  return {
    'GET /org/tree': reply(tree([...BASELINE_NODES, SUB_NODE])),
    'GET /org/locations': reply([LOCATION]),
    'GET /org/designations': page([DESIGNATION]),
  }
}

/** All read routes for employee emp-1 plus the directory. */
export function employeeRoutes(extra: Record<string, MockRoute> = {}): Record<string, MockRoute> {
  return {
    ...orgRoutes(),
    'GET /employees': page([ACTIVE, UNKNOWN, SEPARATED]),
    'GET /employees/emp-1': reply(employee()),
    'GET /employees/emp-1/assignments': reply(ASSIGNMENTS),
    'GET /employees/emp-1/functional-roles': reply(FUNCTIONAL_ROLES),
    'GET /employees/emp-1/responsibilities': reply(RESPONSIBILITIES),
    'GET /employees/emp-1/reporting': reply(REPORTING),
    'GET /employees/emp-1/account': reply(ACCOUNT),
    'GET /employees/emp-1/history': reply(HISTORY_PAGE),
    ...extra,
  }
}

/** Reference data for the CP3/CP4 dialog pickers (synthetic). */
export function pickerRoutes(): Record<string, MockRoute> {
  return {
    'GET /org/grades': reply([ranked('grade-1', 'TEST_G1', 'Test Grade One', 1)]),
    'GET /org/levels': reply([ranked('level-1', 'TEST_L1', 'Test Level One', 1)]),
    'GET /org/functional-roles': page([ROLE]),
    'GET /org/responsibilities': page([RESPONSIBILITY]),
  }
}

/** Read routes plus picker data: everything an HR Admin profile with dialogs loads. */
export function writeRoutes(extra: Record<string, MockRoute> = {}): Record<string, MockRoute> {
  return employeeRoutes({ ...pickerRoutes(), ...extra })
}

export function assignmentWrite(row: (typeof ASSIGNMENTS)[number], warnings: unknown[] = []) {
  return { assignment: row, warnings }
}

/** A separation preview with the given lists (records end the day after the last working day). */
export function separationPreview(overrides: Record<string, unknown> = {}) {
  return {
    employee: ME,
    version: 3,
    separation_date: '2026-12-31',
    records_end_on: '2027-01-01',
    own_records: [],
    direct_reports: [],
    requires_end_open_records: false,
    requires_end_direct_reports: false,
    blocked: false,
    ...overrides,
  }
}

export const OWN_RECORDS = [
  {
    record_id: 'asg-2',
    kind: 'assignment',
    code: 'TEST_MELT',
    name: 'Test Melting',
    effective_from: '2026-07-01',
    effective_to: null,
    starts_after_separation: false,
  },
  {
    record_id: 'rep-2',
    kind: 'reporting_line',
    code: 'T-MGR',
    name: 'Test Manager',
    effective_from: '2026-07-01',
    effective_to: null,
    starts_after_separation: false,
  },
]

export const DIRECT_REPORTS = [
  {
    record_id: 'rep-3',
    employee: employeeRef('emp-sub', 'T-SUB', 'Test Subordinate', null),
    relationship_type: ref('type-line', 'LINE_MANAGER', 'Line manager'),
    effective_from: '2026-08-01',
    effective_to: null,
    starts_after_separation: false,
  },
]
