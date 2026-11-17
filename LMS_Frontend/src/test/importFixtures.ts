/**
 * Synthetic Import Control Room fixtures (Stage D). Never real employee data:
 * codes start with T-, names are "Test Person ...", emails use example.test.
 */

import { reply, type MockRoute } from './renderApp'

export const JOB_ID = '01900000-0000-7000-8000-00000000d001'
const ACTOR = { public_id: '01900000-0000-7000-8000-000000000002', login_id: 'test.hradmin', display_name: 'Test HR Admin' }

export const PROFILE = {
  code: 'employees',
  version: 1,
  commit_mode: 'all_or_nothing_with_explicit_skips',
  can_run: true,
  can_commit: true,
  sections: [
    {
      kind: 'employees',
      sheet_aliases: ['Employees'],
      natural_key: ['employee_code'],
      fields: [
        { name: 'employee_code', type: 'employee_code', required: true, aliases: ['Employee Code', 'Emp Code'], reference: null },
        { name: 'full_name', type: 'text', required: true, aliases: ['Full Name', 'Employee Name'], reference: null },
        { name: 'employment_status', type: 'status', required: false, aliases: ['Employment Status'], reference: null },
        { name: 'date_of_joining', type: 'date', required: false, aliases: ['Date of Joining', 'DOJ'], reference: null },
      ],
    },
    {
      kind: 'assignments',
      sheet_aliases: ['Assignments'],
      natural_key: ['employee_code', 'unit', 'assignment_type', 'effective_from'],
      fields: [
        { name: 'employee_code', type: 'employee_code', required: true, aliases: ['Employee Code'], reference: null },
        { name: 'unit', type: 'reference', required: true, aliases: ['Organisation Unit', 'Department'], reference: 'org_unit' },
        { name: 'designation', type: 'reference', required: false, aliases: ['Designation'], reference: 'designation' },
        { name: 'effective_from', type: 'date', required: true, aliases: ['Effective From'], reference: null },
      ],
    },
  ],
}

export const WORKBOOK = [
  {
    name: 'Employees',
    state: 'visible',
    dimensions: 'A1:E3',
    suggested_section: 'employees',
    header_row: 1,
    headers: [
      { column: 'A', index: 1, text: 'Emp Code', excluded: false, suggested_field: 'employee_code' },
      { column: 'B', index: 2, text: 'Employee Name', excluded: false, suggested_field: 'full_name' },
      { column: 'C', index: 3, text: 'CTC', excluded: true, suggested_field: null },
      { column: 'D', index: 4, text: 'DOJ', excluded: false, suggested_field: 'date_of_joining' },
      { column: 'E', index: 5, text: 'Remarks', excluded: false, suggested_field: null },
    ],
  },
]

export function job(overrides: Record<string, unknown> = {}) {
  return {
    public_id: JOB_ID,
    profile_code: 'employees',
    profile_version: 1,
    status: 'mapping_required',
    original_filename: 'synthetic-people.xlsx',
    file_size: 12_288,
    uploaded_by: ACTOR,
    uploaded_at: '2026-11-16T09:00:00Z',
    validated_at: null,
    committed_at: null,
    finished_at: null,
    counts: {},
    file_sha256: 'a'.repeat(64),
    file_stored: true,
    workbook: WORKBOOK,
    column_mapping: [{ section: 'employees', sheet: 'Employees', header_row: 1, columns: { '1': 'employee_code', '2': 'full_name', '4': 'date_of_joining' } }],
    mapping_confirmed: false,
    previously_imported_by: [],
    failure_code: null,
    validated_by: null,
    committed_by: null,
    version: 1,
    ...overrides,
  }
}

const VALIDATED = {
  validated_at: '2026-11-16T09:05:00Z',
  validated_by: ACTOR,
  mapping_confirmed: true,
}

export const READY = job({
  ...VALIDATED,
  status: 'ready_for_approval',
  version: 4,
  counts: {
    rows: 3,
    blocking_errors: 0,
    error_rows: 0,
    warnings: 1,
    undecided_duplicates: 0,
    importable: 3,
    skipped_rows: 0,
    by_section: { employees: { new: 2, update: 1, unchanged: 0, error: 0, skipped: 0 } },
  },
})

export const FAILED_VALIDATION = job({
  ...VALIDATED,
  status: 'validation_failed',
  version: 3,
  counts: { rows: 2, blocking_errors: 1, warnings: 1, undecided_duplicates: 1, importable: 1, skipped_rows: 0 },
})

export const NEW_ROW = {
  id: 11,
  section: 'employees',
  sheet: 'Employees',
  row_number: 2,
  outcome: 'new',
  values: { employee_code: '00101', full_name: 'Test Person One', date_of_joining: '2025-04-01' },
  source: { employee_code: '00101', full_name: 'Test Person One', date_of_joining: '01-04-2025' },
  changes: null,
  decision: null,
  decision_reason: null,
  target_public_id: null,
  issues: [
    {
      id: 101,
      section: 'employees',
      sheet: 'Employees',
      row_number: 2,
      column: null,
      field: null,
      code: 'probable_duplicate',
      severity: 'warning',
      source_value: null,
      params: { other_codes: ['T-0007'], requires_decision: true },
    },
  ],
}

export const ERROR_ROW = {
  ...NEW_ROW,
  id: 12,
  row_number: 3,
  outcome: 'error',
  values: { employee_code: null, full_name: 'Test Person Two' },
  source: { employee_code: '42', full_name: 'Test Person Two' },
  issues: [
    {
      id: 102,
      section: 'employees',
      sheet: 'Employees',
      row_number: 3,
      column: 'A',
      field: 'employee_code',
      code: 'employee_code_numeric',
      severity: 'error',
      source_value: '42',
      params: { value: '42' },
    },
  ],
}

export const PENDING_MAPPING = {
  public_id: '01900000-0000-7000-8000-00000000e001',
  kind: 'designation',
  source_text: 'Sr. Test Opr',
  normalised_text: 'sr test opr',
  status: 'pending',
  target: null,
  decision_reason: null,
  decided_by: null,
  decided_at: null,
  created_at: '2026-11-16T09:05:00Z',
  suggestions: [
    { public_id: '01900000-0000-7000-8000-00000000f001', code: 'T_SR_OPR', label: 'Test Senior Operator', score: 90, reason: 'abbreviation' },
  ],
  version: 1,
}

export function page(items: unknown[], next_cursor: string | null = null) {
  return { items, next_cursor }
}

/** Read routes of the Import Control Room for one job. */
export function importRoutes(current: unknown, extra: Record<string, MockRoute> = {}): Record<string, MockRoute> {
  return {
    'GET /imports/profiles': reply([PROFILE]),
    'GET /imports': reply(page([current])),
    [`GET /imports/${JOB_ID}`]: reply(current),
    [`GET /imports/${JOB_ID}/rows`]: reply(page([NEW_ROW, ERROR_ROW])),
    [`GET /imports/${JOB_ID}/issues`]: reply(page([...NEW_ROW.issues, ...ERROR_ROW.issues])),
    'GET /imports/mappings': reply(page([PENDING_MAPPING])),
    ...extra,
  }
}
