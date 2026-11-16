import { describe, expect, it } from 'vitest'

import { ACCOUNT, ACTIVE, ASSIGNMENTS, employee, FUNCTIONAL_ROLES, UNKNOWN } from '../test/employeeFixtures'
import { mockApi, reply } from '../test/renderApp'
import {
  employeeService,
  parseEmployee,
  parseEmployeeAccount,
  parseEmployeeSummary,
  parseFunctionalRoles,
  parseSeparationPreview,
} from './employeeService'

const PREVIEW = {
  employee: { public_id: 'emp-1', employee_code: '00042', full_name: 'Test Person One', employment_status: 'active' },
  version: 3,
  separation_date: '2026-06-30',
  records_end_on: '2026-07-01',
  own_records: [
    {
      record_id: 'asg-1',
      kind: 'assignment',
      code: 'OPERATION',
      name: 'Operation',
      effective_from: '2025-04-01',
      effective_to: null,
      starts_after_separation: false,
    },
  ],
  direct_reports: [],
  requires_end_open_records: true,
  requires_end_direct_reports: false,
  blocked: false,
}

describe('employee parsers', () => {
  it('keeps an unrecorded status as null and copies only known fields', () => {
    const parsed = parseEmployeeSummary({ ...UNKNOWN, salary: 1, internal_id: 7 })
    expect(parsed.employment_status).toBeNull()
    expect(Object.keys(parsed).sort()).toEqual(Object.keys(UNKNOWN).sort())
  })

  it('keeps employee codes as text (leading zeros)', () => {
    expect(parseEmployee(employee()).employee_code).toBe('00042')
  })

  it('rejects unknown statuses, assignment types and malformed lists', () => {
    expect(() => parseEmployeeSummary({ ...ACTIVE, employment_status: 'retired' })).toThrow(TypeError)
    expect(() => parseEmployee({ ...employee(), accounts: 'none' })).toThrow(TypeError)
    expect(() =>
      parseFunctionalRoles({ ...FUNCTIONAL_ROLES, records: [{ ...FUNCTIONAL_ROLES.records[0], kind: 'other' }] }),
    ).toThrow(TypeError)
  })

  it('parses account summaries without network details', () => {
    const parsed = parseEmployeeAccount(ACCOUNT)
    expect(parsed.flags).toEqual(['email_mismatch'])
    expect(parsed.history[0].source_ip).toBeNull()
    expect(parsed.history[0].user_agent).toBeNull()
  })

  it('parses the separation preview exactly', () => {
    expect(parseSeparationPreview(PREVIEW)).toEqual(PREVIEW)
    expect(() => parseSeparationPreview({ ...PREVIEW, records_end_on: 'tomorrow' })).toThrow(TypeError)
  })
})

describe('employeeService', () => {
  it('sends exactly the API parameter names for the directory', async () => {
    const api = mockApi({ 'GET /employees': reply({ items: [ACTIVE], next_cursor: 'c2' }) })

    await employeeService.list(
      {
        q: '0004',
        status: 'unknown',
        unit: 'unit-ops',
        include_descendants: true,
        location: 'loc-1',
        designation: 'des-1',
        has_account: false,
        as_of: '2026-06-30',
      },
      'c1',
    )
    await employeeService.list({ include_descendants: true }, null)

    const [full, plain] = api.requestsTo('GET /employees')
    expect(Object.fromEntries(full.query)).toEqual({
      q: '0004',
      status: 'unknown',
      unit: 'unit-ops',
      include_descendants: 'true',
      location: 'loc-1',
      designation: 'des-1',
      has_account: 'false',
      as_of: '2026-06-30',
      limit: '50',
      cursor: 'c1',
    })
    // include_descendants only makes sense with a unit.
    expect(Object.fromEntries(plain.query)).toEqual({ limit: '50' })
  })

  it('reads the profile sections with their query parameters', async () => {
    const api = mockApi({
      'GET /employees/emp-1': reply(employee()),
      'GET /employees/emp-1/assignments': reply(ASSIGNMENTS),
      'GET /employees/emp-1/functional-roles': reply(FUNCTIONAL_ROLES),
    })

    await employeeService.get('emp-1', '2026-02-01')
    await employeeService.listAssignments('emp-1', false)
    await employeeService.getFunctionalRoles('emp-1', undefined, true)

    expect(Object.fromEntries(api.requestsTo('GET /employees/emp-1')[0].query)).toEqual({ as_of: '2026-02-01' })
    expect(Object.fromEntries(api.requestsTo('GET /employees/emp-1/assignments')[0].query)).toEqual({
      include_ended: 'false',
    })
    expect(Object.fromEntries(api.requestsTo('GET /employees/emp-1/functional-roles')[0].query)).toEqual({
      include_ended: 'true',
    })
  })

  it('sends the last working day to the preview unchanged', async () => {
    const api = mockApi({ 'GET /employees/emp-1/separation-preview': reply(PREVIEW) })

    const preview = await employeeService.previewSeparation('emp-1', '2026-06-30')

    const [request] = api.requestsTo('GET /employees/emp-1/separation-preview')
    expect(Object.fromEntries(request.query)).toEqual({ separation_date: '2026-06-30' })
    expect(preview.records_end_on).toBe('2026-07-01') // the server adds the day, once
    expect(request.method).toBe('GET')
  })
})

describe('employee changes', () => {
  const SEPARATED = employee(ACTIVE, { employment_status: 'separated', date_of_separation: '2026-06-30' })

  it('sends every change to its documented method and path with the body unchanged', async () => {
    const asg = { assignment: ASSIGNMENTS[1], warnings: [] }
    const role = FUNCTIONAL_ROLES.records[0]
    const api = mockApi({
      'POST /employees': reply(employee(), 201),
      'PATCH /employees/emp-1': reply(employee()),
      'POST /employees/emp-1/employment-status': reply(SEPARATED),
      'POST /employees/emp-1/assignments': reply(asg, 201),
      'POST /employees/emp-1/assignments/asg-2/change': reply(asg, 201),
      'POST /employees/emp-1/assignments/asg-2/end': reply(ASSIGNMENTS[1]),
      'PATCH /employees/emp-1/assignments/asg-2': reply(asg),
      'POST /employees/emp-1/functional-roles': reply(role, 201),
      'POST /employees/emp-1/functional-roles/fr-1/end': reply(role),
      'PUT /employees/emp-1/account': reply(ACCOUNT),
      'POST /employees/emp-1/account/unlink': reply(ACCOUNT),
    })
    const statusBody = {
      version: 3,
      status: 'separated' as const,
      separation_date: '2026-06-30',
      end_open_records: true,
      end_direct_reports: false,
      reason: null,
    }
    await employeeService.changeStatus('emp-1', statusBody)
    await employeeService.correct('emp-1', { version: 3, reason: null, display_name: 'X' })
    await employeeService.changeAssignment('emp-1', 'asg-2', { version: 1, effective_date: '2026-09-01', reason: null })
    await employeeService.endAssignment('emp-1', 'asg-2', { version: 1, effective_to: '2026-10-01', reason: null })
    await employeeService.correctAssignment('emp-1', 'asg-2', { version: 1, reason: 'Wrong', assignment_type: 'acting' })
    await employeeService.endRole('emp-1', 'fr-1', { effective_to: '2026-10-01', reason: null })
    await employeeService.linkAccount('emp-1', { user_public_id: 'acc-9', reason: null })
    await employeeService.unlinkAccount('emp-1', { user_public_id: 'acc-9', reason: null })

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      'POST /employees/emp-1/employment-status',
      'PATCH /employees/emp-1',
      'POST /employees/emp-1/assignments/asg-2/change',
      'POST /employees/emp-1/assignments/asg-2/end',
      'PATCH /employees/emp-1/assignments/asg-2',
      'POST /employees/emp-1/functional-roles/fr-1/end',
      'PUT /employees/emp-1/account',
      'POST /employees/emp-1/account/unlink',
    ])
    // The separation date (last working day) is sent exactly as given - never +1.
    expect(api.requests[0].body).toEqual(statusBody)
  })

  it('parses assignment writes with their advisory warnings', async () => {
    mockApi({
      'POST /employees/emp-1/assignments': reply(
        { assignment: ASSIGNMENTS[1], warnings: [{ code: 'unit_type_not_assignable', message: 'x' }] },
        201,
      ),
    })
    const result = await employeeService.createAssignment('emp-1', {
      assignment_type: 'primary',
      org_unit_id: 'unit-melt',
      designation_id: null,
      grade_id: null,
      job_level_id: null,
      location_id: null,
      effective_from: '2026-07-01',
      effective_to: null,
      reason: null,
    })
    expect(result.assignment.public_id).toBe('asg-2')
    expect(result.warnings).toEqual([{ code: 'unit_type_not_assignable', message: 'x' }])
  })

  it('rejects a malformed write response', async () => {
    mockApi({ 'POST /employees/emp-1/assignments/asg-2/end': reply({ public_id: 'asg-2' }) })
    await expect(
      employeeService.endAssignment('emp-1', 'asg-2', { version: 1, effective_to: '2026-10-01', reason: null }),
    ).rejects.toThrow()
  })
})
