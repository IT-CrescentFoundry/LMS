/**
 * Employee master API (Stage C3 endpoints under `/employees`).
 *
 * Reads need `employees.view` (assignment timeline and history:
 * `employees.history.view`; data quality and the separation preview:
 * `employees.manage`). The backend enforces every permission; the UI only hides
 * what a user cannot use. Parsers copy known fields only.
 */

import { apiRequest, buildQuery, isRecord } from '../lib/apiClient'
import {
  expectBoolean,
  expectDateString,
  expectInteger,
  expectIsoDate,
  expectNullableIsoDate,
  expectNullableString,
  expectOneOf,
  expectRecord,
  expectString,
} from '../lib/parse'
import type { Page } from '../types/admin'
import {
  ASSIGNMENT_TYPES,
  DATA_QUALITY_CHECKS,
  EMPLOYEE_LANGUAGES,
  EMPLOYMENT_STATUSES,
  ROLE_RECORD_KINDS,
  SEPARATION_RECORD_KINDS,
  type AccountLinkBody,
  type AccountRef,
  type Assignment,
  type AssignmentChangeBody,
  type AssignmentCorrectionBody,
  type AssignmentCreateBody,
  type AssignmentEndBody,
  type AssignmentWrite,
  type DataQuality,
  type DataQualityCheck,
  type DerivedFrom,
  type DirectReport,
  type EffectiveRole,
  type Employee,
  type EmployeeAccount,
  type EmployeeCorrectionBody,
  type EmployeeCreateBody,
  type EmployeeFilters,
  type EmployeeRef,
  type EmployeeSummary,
  type EmployeeWarning,
  type EmploymentStatus,
  type FunctionalRoles,
  type ManagerSetBody,
  type RecordEndBody,
  type Reporting,
  type ReportingRecord,
  type ReportingType,
  type ResponsibilityAssignBody,
  type ResponsibilityRecord,
  type RoleAssignBody,
  type RoleRecord,
  type SeparationPreview,
  type SeparationRecord,
  type StatusChangeBody,
} from '../types/employee'
import type { Ref } from '../types/organisation'
import { parseAuditEvent, parsePage } from './adminService'
import { parseRef } from './organisationService'

export const EMPLOYEE_PAGE_SIZE = 50
export const HISTORY_PAGE_SIZE = 50
export const EMPLOYEE_PICKER_SIZE = 20

// ------------------------------------------------------------------- parsers

function list<T>(data: unknown, what: string, parseItem: (item: unknown) => T): T[] {
  if (!Array.isArray(data)) throw new TypeError(`${what}: expected a list`)
  return data.map(parseItem)
}

function nullableRef(data: unknown): Ref | null {
  return data === null || data === undefined ? null : parseRef(data)
}

function nullableStatus(record: Record<string, unknown>): EmploymentStatus | null {
  return record.employment_status === null || record.employment_status === undefined
    ? null
    : expectOneOf(record, 'employment_status', EMPLOYMENT_STATUSES)
}

export function parseEmployeeRef(data: unknown): EmployeeRef {
  const record = expectRecord(data, 'employee reference')
  return {
    public_id: expectString(record, 'public_id'),
    employee_code: expectString(record, 'employee_code'),
    full_name: expectString(record, 'full_name'),
    employment_status: nullableStatus(record),
  }
}

function parseAccountRef(data: unknown): AccountRef {
  const record = expectRecord(data, 'account')
  return {
    public_id: expectString(record, 'public_id'),
    login_id: expectString(record, 'login_id'),
    display_name: expectString(record, 'display_name'),
    status: expectString(record, 'status'),
  }
}

function summaryFields(record: Record<string, unknown>): EmployeeSummary {
  return {
    public_id: expectString(record, 'public_id'),
    employee_code: expectString(record, 'employee_code'),
    full_name: expectString(record, 'full_name'),
    display_name: expectNullableString(record, 'display_name'),
    employment_status: nullableStatus(record),
    as_of: expectIsoDate(record, 'as_of'),
    primary_unit: nullableRef(record.primary_unit),
    path: list(record.path, 'path', parseRef),
    designation: nullableRef(record.designation),
    location: nullableRef(record.location),
    line_manager:
      record.line_manager === null || record.line_manager === undefined
        ? null
        : parseEmployeeRef(record.line_manager),
    has_active_account: expectBoolean(record, 'has_active_account'),
  }
}

export function parseEmployeeSummary(data: unknown): EmployeeSummary {
  return summaryFields(expectRecord(data, 'employee'))
}

export function parseEmployee(data: unknown): Employee {
  const record = expectRecord(data, 'employee')
  return {
    ...summaryFields(record),
    preferred_language:
      record.preferred_language === null || record.preferred_language === undefined
        ? null
        : expectOneOf(record, 'preferred_language', EMPLOYEE_LANGUAGES),
    work_email: expectNullableString(record, 'work_email'),
    date_of_joining: expectNullableIsoDate(record, 'date_of_joining'),
    date_of_separation: expectNullableIsoDate(record, 'date_of_separation'),
    external_ref: expectNullableString(record, 'external_ref'),
    accounts: list(record.accounts, 'accounts', parseAccountRef),
    version: expectInteger(record, 'version'),
    created_at: expectDateString(record, 'created_at'),
    updated_at: expectDateString(record, 'updated_at'),
  }
}

export function parseAssignment(data: unknown): Assignment {
  const record = expectRecord(data, 'assignment')
  return {
    public_id: expectString(record, 'public_id'),
    assignment_type: expectOneOf(record, 'assignment_type', ASSIGNMENT_TYPES),
    org_unit: parseRef(record.org_unit),
    designation: nullableRef(record.designation),
    grade: nullableRef(record.grade),
    job_level: nullableRef(record.job_level),
    location: nullableRef(record.location),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    source: expectString(record, 'source'),
    reason: expectNullableString(record, 'reason'),
    version: expectInteger(record, 'version'),
    created_at: expectDateString(record, 'created_at'),
    updated_at: expectDateString(record, 'updated_at'),
  }
}

function parseWarnings(data: unknown): EmployeeWarning[] {
  if (data === undefined || data === null) return []
  return list(data, 'warnings', (item) => {
    const record = expectRecord(item, 'warning')
    return { code: expectString(record, 'code'), message: expectString(record, 'message') }
  })
}

export function parseAssignmentWrite(data: unknown): AssignmentWrite {
  const record = expectRecord(data, 'assignment change')
  return { assignment: parseAssignment(record.assignment), warnings: parseWarnings(record.warnings) }
}

export function parseRoleRecord(data: unknown): RoleRecord {
  const record = expectRecord(data, 'functional role record')
  return {
    public_id: expectString(record, 'public_id'),
    functional_role: parseRef(record.functional_role),
    kind: expectOneOf(record, 'kind', ROLE_RECORD_KINDS),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    reason: expectNullableString(record, 'reason'),
    created_at: expectDateString(record, 'created_at'),
  }
}

function parseDerivedFrom(data: unknown): DerivedFrom {
  const record = expectRecord(data, 'derivation')
  return {
    assignment: expectString(record, 'assignment'),
    assignment_type: expectOneOf(record, 'assignment_type', ASSIGNMENT_TYPES),
    org_unit: parseRef(record.org_unit),
    designation: parseRef(record.designation),
    mapping: expectString(record, 'mapping'),
  }
}

function parseEffectiveRole(data: unknown): EffectiveRole {
  const record = expectRecord(data, 'effective role')
  return {
    functional_role: parseRef(record.functional_role),
    effective: expectBoolean(record, 'effective'),
    derived_from: list(record.derived_from, 'derived_from', parseDerivedFrom),
    manual: record.manual ? parseRoleRecord(record.manual) : null,
    exclusion: record.exclusion ? parseRoleRecord(record.exclusion) : null,
  }
}

export function parseFunctionalRoles(data: unknown): FunctionalRoles {
  const record = expectRecord(data, 'functional roles')
  return {
    as_of: expectIsoDate(record, 'as_of'),
    roles: list(record.roles, 'roles', parseEffectiveRole),
    records: list(record.records, 'records', parseRoleRecord),
  }
}

export function parseResponsibilityRecord(data: unknown): ResponsibilityRecord {
  const record = expectRecord(data, 'responsibility record')
  return {
    public_id: expectString(record, 'public_id'),
    responsibility: parseRef(record.responsibility),
    context_unit: nullableRef(record.context_unit),
    context_location: nullableRef(record.context_location),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    reason: expectNullableString(record, 'reason'),
    created_at: expectDateString(record, 'created_at'),
  }
}

export function parseReportingRecord(data: unknown): ReportingRecord {
  const record = expectRecord(data, 'reporting relationship')
  return {
    public_id: expectString(record, 'public_id'),
    relationship_type: parseRef(record.relationship_type),
    employee: parseEmployeeRef(record.employee),
    manager: parseEmployeeRef(record.manager),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    reason: expectNullableString(record, 'reason'),
    created_at: expectDateString(record, 'created_at'),
  }
}

export function parseReporting(data: unknown): Reporting {
  const record = expectRecord(data, 'reporting')
  return {
    as_of: expectIsoDate(record, 'as_of'),
    managers: list(record.managers, 'managers', parseReportingRecord),
    history: list(record.history, 'history', parseReportingRecord),
    direct_reports: list(record.direct_reports, 'direct_reports', parseReportingRecord),
  }
}

function parseReportingType(data: unknown): ReportingType {
  const record = expectRecord(data, 'reporting type')
  const translations: ReportingType['translations'] = {}
  if (isRecord(record.translations)) {
    for (const locale of ['bn', 'hi', 'gu'] as const) {
      const value = record.translations[locale]
      if (typeof value === 'string' && value.trim() !== '') translations[locale] = value
    }
  }
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    allows_multiple: expectBoolean(record, 'allows_multiple'),
    is_hierarchical: expectBoolean(record, 'is_hierarchical'),
    is_active: expectBoolean(record, 'is_active'),
    translations,
  }
}

export function parseEmployeeAccount(data: unknown): EmployeeAccount {
  const record = expectRecord(data, 'employee account')
  if (!Array.isArray(record.flags) || !record.flags.every((flag) => typeof flag === 'string')) {
    throw new TypeError('flags: expected a list of strings')
  }
  return {
    accounts: list(record.accounts, 'accounts', parseAccountRef),
    flags: [...record.flags],
    history: list(record.history, 'history', parseAuditEvent),
  }
}

export function parseDataQuality(data: unknown): DataQuality {
  const record = expectRecord(data, 'data quality')
  if (!isRecord(record.counts)) throw new TypeError('counts: expected an object')
  const counts: DataQuality['counts'] = {}
  for (const check of DATA_QUALITY_CHECKS) {
    const value = record.counts[check]
    if (typeof value === 'number' && Number.isInteger(value)) counts[check] = value
  }
  return {
    as_of: expectIsoDate(record, 'as_of'),
    counts,
    check: expectNullableString(record, 'check'),
    items: list(record.items, 'items', parseEmployeeSummary),
    next_cursor: expectNullableString(record, 'next_cursor'),
  }
}

function parseSeparationRecord(data: unknown): SeparationRecord {
  const record = expectRecord(data, 'separation record')
  return {
    record_id: expectString(record, 'record_id'),
    kind: expectOneOf(record, 'kind', SEPARATION_RECORD_KINDS),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    starts_after_separation: expectBoolean(record, 'starts_after_separation'),
  }
}

function parseDirectReport(data: unknown): DirectReport {
  const record = expectRecord(data, 'direct report')
  return {
    record_id: expectString(record, 'record_id'),
    employee: parseEmployeeRef(record.employee),
    relationship_type: parseRef(record.relationship_type),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    starts_after_separation: expectBoolean(record, 'starts_after_separation'),
  }
}

export function parseSeparationPreview(data: unknown): SeparationPreview {
  const record = expectRecord(data, 'separation preview')
  return {
    employee: parseEmployeeRef(record.employee),
    version: expectInteger(record, 'version'),
    separation_date: expectIsoDate(record, 'separation_date'),
    records_end_on: expectIsoDate(record, 'records_end_on'),
    own_records: list(record.own_records, 'own_records', parseSeparationRecord),
    direct_reports: list(record.direct_reports, 'direct_reports', parseDirectReport),
    requires_end_open_records: expectBoolean(record, 'requires_end_open_records'),
    requires_end_direct_reports: expectBoolean(record, 'requires_end_direct_reports'),
    blocked: expectBoolean(record, 'blocked'),
  }
}

// ------------------------------------------------------------------- service

function path(employeeId: string, suffix = ''): string {
  return `/employees/${encodeURIComponent(employeeId)}${suffix}`
}

function child(employeeId: string, collection: string, recordId: string, suffix = ''): string {
  return path(employeeId, `/${collection}/${encodeURIComponent(recordId)}${suffix}`)
}

function send<T>(
  target: string,
  method: 'POST' | 'PUT' | 'PATCH',
  body: object,
  parse: (data: unknown) => T,
): Promise<T> {
  return apiRequest(target, { method, body, parse })
}

export const employeeService = {
  /** `GET /employees` - the directory (`employees.view`). */
  list(
    filters: EmployeeFilters,
    cursor: string | null,
    signal?: AbortSignal,
    limit: number = EMPLOYEE_PAGE_SIZE,
  ): Promise<Page<EmployeeSummary>> {
    const query = buildQuery({
      q: filters.q,
      status: filters.status,
      unit: filters.unit,
      include_descendants: filters.unit ? filters.include_descendants : undefined,
      location: filters.location,
      designation: filters.designation,
      has_account: filters.has_account,
      as_of: filters.as_of,
      limit,
      cursor,
    })
    return apiRequest(`/employees${query}`, { parse: parsePage(parseEmployeeSummary), signal })
  },

  get(employeeId: string, asOf: string | undefined, signal?: AbortSignal): Promise<Employee> {
    return apiRequest(`${path(employeeId)}${buildQuery({ as_of: asOf })}`, {
      parse: parseEmployee,
      signal,
    })
  },

  /** `employees.history.view`. */
  listAssignments(
    employeeId: string,
    includeEnded: boolean,
    signal?: AbortSignal,
  ): Promise<Assignment[]> {
    return apiRequest(
      `${path(employeeId, '/assignments')}${buildQuery({ include_ended: includeEnded })}`,
      { parse: (data) => list(data, 'assignments', parseAssignment), signal },
    )
  },

  getFunctionalRoles(
    employeeId: string,
    asOf: string | undefined,
    includeEnded: boolean,
    signal?: AbortSignal,
  ): Promise<FunctionalRoles> {
    return apiRequest(
      `${path(employeeId, '/functional-roles')}${buildQuery({ as_of: asOf, include_ended: includeEnded })}`,
      { parse: parseFunctionalRoles, signal },
    )
  },

  listResponsibilities(
    employeeId: string,
    includeEnded: boolean,
    signal?: AbortSignal,
  ): Promise<ResponsibilityRecord[]> {
    return apiRequest(
      `${path(employeeId, '/responsibilities')}${buildQuery({ include_ended: includeEnded })}`,
      { parse: (data) => list(data, 'responsibilities', parseResponsibilityRecord), signal },
    )
  },

  getReporting(employeeId: string, asOf: string | undefined, signal?: AbortSignal): Promise<Reporting> {
    return apiRequest(`${path(employeeId, '/reporting')}${buildQuery({ as_of: asOf })}`, {
      parse: parseReporting,
      signal,
    })
  },

  listReportingTypes(signal?: AbortSignal): Promise<ReportingType[]> {
    return apiRequest('/employees/reporting-types', {
      parse: (data) => list(data, 'reporting types', parseReportingType),
      signal,
    })
  },

  getAccount(employeeId: string, signal?: AbortSignal): Promise<EmployeeAccount> {
    return apiRequest(path(employeeId, '/account'), { parse: parseEmployeeAccount, signal })
  },

  /** `employees.history.view`; newest first. Network details are never included. */
  listHistory(employeeId: string, cursor: string | null, signal?: AbortSignal) {
    return apiRequest(
      `${path(employeeId, '/history')}${buildQuery({ limit: HISTORY_PAGE_SIZE, cursor })}`,
      { parse: parsePage(parseAuditEvent), signal },
    )
  },

  /** `employees.manage`; counts for every check plus one page of a selected check. */
  getDataQuality(
    asOf: string | undefined,
    check: DataQualityCheck | null,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<DataQuality> {
    return apiRequest(
      `/employees/data-quality${buildQuery({ as_of: asOf, check, limit: EMPLOYEE_PAGE_SIZE, cursor })}`,
      { parse: parseDataQuality, signal },
    )
  },

  /**
   * `employees.manage`; read-only. `lastWorkingDay` is sent unchanged - the server
   * reports the exclusive end (`records_end_on`, the following day) itself.
   */
  previewSeparation(
    employeeId: string,
    lastWorkingDay: string,
    signal?: AbortSignal,
  ): Promise<SeparationPreview> {
    return apiRequest(
      `${path(employeeId, '/separation-preview')}${buildQuery({ separation_date: lastWorkingDay })}`,
      { parse: parseSeparationPreview, signal },
    )
  },

  // ----------------------------------------------------------------- changes
  // All need `employees.manage`, except reporting lines (`reporting_lines.manage`)
  // and account links (`employees.manage` AND `user_accounts.manage`).

  create(body: EmployeeCreateBody): Promise<Employee> {
    return send('/employees', 'POST', body, parseEmployee)
  },

  /** Correction of recorded details (changed fields only, with `version`). */
  correct(employeeId: string, body: EmployeeCorrectionBody): Promise<Employee> {
    return send(path(employeeId), 'PATCH', body, parseEmployee)
  },

  /** Status change and separation. `separation_date` is the last working day, unchanged. */
  changeStatus(employeeId: string, body: StatusChangeBody): Promise<Employee> {
    return send(path(employeeId, '/employment-status'), 'POST', body, parseEmployee)
  },

  createAssignment(employeeId: string, body: AssignmentCreateBody): Promise<AssignmentWrite> {
    return send(path(employeeId, '/assignments'), 'POST', body, parseAssignmentWrite)
  },

  changeAssignment(employeeId: string, assignmentId: string, body: AssignmentChangeBody): Promise<AssignmentWrite> {
    return send(child(employeeId, 'assignments', assignmentId, '/change'), 'POST', body, parseAssignmentWrite)
  },

  endAssignment(employeeId: string, assignmentId: string, body: AssignmentEndBody): Promise<Assignment> {
    return send(child(employeeId, 'assignments', assignmentId, '/end'), 'POST', body, parseAssignment)
  },

  correctAssignment(
    employeeId: string,
    assignmentId: string,
    body: AssignmentCorrectionBody,
  ): Promise<AssignmentWrite> {
    return send(child(employeeId, 'assignments', assignmentId), 'PATCH', body, parseAssignmentWrite)
  },

  assignRole(employeeId: string, body: RoleAssignBody): Promise<RoleRecord> {
    return send(path(employeeId, '/functional-roles'), 'POST', body, parseRoleRecord)
  },

  endRole(employeeId: string, recordId: string, body: RecordEndBody): Promise<RoleRecord> {
    return send(child(employeeId, 'functional-roles', recordId, '/end'), 'POST', body, parseRoleRecord)
  },

  assignResponsibility(employeeId: string, body: ResponsibilityAssignBody): Promise<ResponsibilityRecord> {
    return send(path(employeeId, '/responsibilities'), 'POST', body, parseResponsibilityRecord)
  },

  endResponsibility(employeeId: string, recordId: string, body: RecordEndBody): Promise<ResponsibilityRecord> {
    return send(child(employeeId, 'responsibilities', recordId, '/end'), 'POST', body, parseResponsibilityRecord)
  },

  /** `reporting_lines.manage`. Replaces the current line manager from `effective_from`. */
  setManager(employeeId: string, body: ManagerSetBody): Promise<ReportingRecord> {
    return send(path(employeeId, '/reporting'), 'POST', body, parseReportingRecord)
  },

  endReporting(employeeId: string, recordId: string, body: RecordEndBody): Promise<ReportingRecord> {
    return send(child(employeeId, 'reporting', recordId, '/end'), 'POST', body, parseReportingRecord)
  },

  linkAccount(employeeId: string, body: AccountLinkBody): Promise<EmployeeAccount> {
    return send(path(employeeId, '/account'), 'PUT', body, parseEmployeeAccount)
  },

  unlinkAccount(employeeId: string, body: AccountLinkBody): Promise<EmployeeAccount> {
    return send(path(employeeId, '/account/unlink'), 'POST', body, parseEmployeeAccount)
  },
}
