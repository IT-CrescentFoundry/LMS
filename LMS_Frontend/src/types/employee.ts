/**
 * Mirrors the Stage C3 schemas in LMS_Backend/app/schemas/employees.py (see
 * docs/architecture/API_REFERENCE.md section 9).
 *
 * Employee records are separate from login accounts. Dates are business dates
 * (YYYY-MM-DD). Periods are half-open: `effective_to` is the first day a record no
 * longer applies (the UI shows the last day, `effective_to - 1`).
 */

import type { AuditEvent } from './admin'
import type { Ref } from './organisation'

/** `null` means the status has not been recorded; it is never treated as active. */
export const EMPLOYMENT_STATUSES = ['active', 'on_leave', 'separated'] as const
export type EmploymentStatus = (typeof EMPLOYMENT_STATUSES)[number]

/** Directory filter values; `unknown` selects employees whose status is not recorded. */
export const STATUS_FILTERS = ['active', 'on_leave', 'separated', 'unknown'] as const
export type StatusFilter = (typeof STATUS_FILTERS)[number]

export const ASSIGNMENT_TYPES = ['primary', 'additional', 'acting', 'deputation'] as const
export type AssignmentType = (typeof ASSIGNMENT_TYPES)[number]

export const ROLE_RECORD_KINDS = ['manual', 'exclusion'] as const
export type RoleRecordKind = (typeof ROLE_RECORD_KINDS)[number]

export const EMPLOYEE_LANGUAGES = ['en', 'bn', 'hi', 'gu'] as const
export type EmployeeLanguage = (typeof EMPLOYEE_LANGUAGES)[number]

export const DATA_QUALITY_CHECKS = [
  'unknown_status',
  'no_primary_assignment',
  'missing_location',
  'missing_designation',
  'separated_with_active_account',
  'manager_inactive',
  'no_line_manager',
  'incomplete_record',
] as const
export type DataQualityCheck = (typeof DATA_QUALITY_CHECKS)[number]

export const ACCOUNT_FLAGS = ['separated_with_active_account', 'email_mismatch'] as const
export type AccountFlag = (typeof ACCOUNT_FLAGS)[number]

export interface EmployeeRef {
  public_id: string
  employee_code: string
  full_name: string
  employment_status: EmploymentStatus | null
}

/** A linked login account. Never contains credentials or tokens. */
export interface AccountRef {
  public_id: string
  login_id: string
  display_name: string
  status: string
}

export interface EmployeeSummary {
  public_id: string
  employee_code: string
  full_name: string
  display_name: string | null
  employment_status: EmploymentStatus | null
  as_of: string
  primary_unit: Ref | null
  /** Ancestors of the primary unit on `as_of`, root first (computed by the server). */
  path: Ref[]
  designation: Ref | null
  location: Ref | null
  line_manager: EmployeeRef | null
  has_active_account: boolean
}

export interface Employee extends EmployeeSummary {
  preferred_language: EmployeeLanguage | null
  work_email: string | null
  date_of_joining: string | null
  /** The last working day. */
  date_of_separation: string | null
  external_ref: string | null
  accounts: AccountRef[]
  version: number
  created_at: string
  updated_at: string
}

export interface EmployeeFilters {
  q?: string
  status?: StatusFilter
  /** Organisation unit public_id. */
  unit?: string
  include_descendants?: boolean
  location?: string
  designation?: string
  has_account?: boolean
  as_of?: string
}

export interface Assignment {
  public_id: string
  assignment_type: AssignmentType
  org_unit: Ref
  designation: Ref | null
  grade: Ref | null
  job_level: Ref | null
  location: Ref | null
  effective_from: string | null
  /** Exclusive end; null while open. */
  effective_to: string | null
  source: string
  reason: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface RoleRecord {
  public_id: string
  functional_role: Ref
  kind: RoleRecordKind
  effective_from: string | null
  effective_to: string | null
  reason: string | null
  created_at: string
}

export interface DerivedFrom {
  assignment: string
  assignment_type: AssignmentType
  org_unit: Ref
  designation: Ref
  mapping: string
}

export interface EffectiveRole {
  functional_role: Ref
  /** False when an exclusion hides the role. */
  effective: boolean
  derived_from: DerivedFrom[]
  manual: RoleRecord | null
  exclusion: RoleRecord | null
}

export interface FunctionalRoles {
  as_of: string
  roles: EffectiveRole[]
  records: RoleRecord[]
}

export interface ResponsibilityRecord {
  public_id: string
  responsibility: Ref
  context_unit: Ref | null
  context_location: Ref | null
  effective_from: string | null
  effective_to: string | null
  reason: string | null
  created_at: string
}

export interface ReportingRecord {
  public_id: string
  relationship_type: Ref
  employee: EmployeeRef
  manager: EmployeeRef
  effective_from: string | null
  effective_to: string | null
  reason: string | null
  created_at: string
}

export interface Reporting {
  as_of: string
  managers: ReportingRecord[]
  history: ReportingRecord[]
  direct_reports: ReportingRecord[]
}

export interface ReportingType {
  public_id: string
  code: string
  name: string
  allows_multiple: boolean
  is_hierarchical: boolean
  is_active: boolean
  translations: Partial<Record<'bn' | 'hi' | 'gu', string>>
}

export interface EmployeeAccount {
  /** Linked accounts, including disabled ones (kept as history). */
  accounts: AccountRef[]
  flags: string[]
  /** Link and unlink events, newest first (no source IP or user agent). */
  history: AuditEvent[]
}

export interface DataQuality {
  as_of: string
  counts: Partial<Record<DataQualityCheck, number>>
  check: string | null
  items: EmployeeSummary[]
  next_cursor: string | null
}

export const SEPARATION_RECORD_KINDS = [
  'assignment',
  'functional_role',
  'responsibility',
  'reporting_line',
] as const
export type SeparationRecordKind = (typeof SEPARATION_RECORD_KINDS)[number]

export interface SeparationRecord {
  record_id: string
  kind: SeparationRecordKind
  code: string
  name: string
  effective_from: string | null
  effective_to: string | null
  starts_after_separation: boolean
}

export interface DirectReport {
  record_id: string
  /** The subordinate. */
  employee: EmployeeRef
  relationship_type: Ref
  effective_from: string | null
  effective_to: string | null
  starts_after_separation: boolean
}

/** Read-only impact of a separation (GET .../separation-preview). */
export interface SeparationPreview {
  employee: EmployeeRef
  version: number
  /** The last working day, exactly as requested. */
  separation_date: string
  /** The exclusive end the ended records would get (the following day). */
  records_end_on: string
  own_records: SeparationRecord[]
  direct_reports: DirectReport[]
  requires_end_open_records: boolean
  requires_end_direct_reports: boolean
  blocked: boolean
}

// ------------------------------------------------------------- request bodies
// Exactly the fields of the C3a request schemas. End dates (`effective_to`) are
// EXCLUSIVE; dialogs build them from an entered last day with `lastDayToEnd`.

export interface EmployeeCreateBody {
  employee_code: string
  full_name: string
  display_name: string | null
  preferred_language: EmployeeLanguage | null
  work_email: string | null
  /** null = not recorded. */
  employment_status: EmploymentStatus | null
  date_of_joining: string | null
  /** Last working day; only (and always) with `separated`. */
  date_of_separation: string | null
  external_ref: string | null
}

/** PATCH /employees/{id}: changed fields only. Status uses the status endpoint. */
export interface EmployeeCorrectionBody {
  version: number
  reason: string | null
  employee_code?: string
  full_name?: string
  display_name?: string | null
  preferred_language?: EmployeeLanguage | null
  work_email?: string | null
  date_of_joining?: string | null
  external_ref?: string | null
}

export interface StatusChangeBody {
  version: number
  status: EmploymentStatus
  /** Last working day, sent UNCHANGED (never through lastDayToEnd); separated only. */
  separation_date: string | null
  end_open_records: boolean
  end_direct_reports: boolean
  reason: string | null
}

export interface AssignmentCreateBody {
  assignment_type: AssignmentType
  org_unit_id: string
  designation_id: string | null
  grade_id: string | null
  job_level_id: string | null
  location_id: string | null
  effective_from: string
  effective_to: string | null
  reason: string | null
}

/** Business change from `effective_date` (sent unchanged); changed fields only. */
export interface AssignmentChangeBody {
  version: number
  effective_date: string
  reason: string | null
  org_unit_id?: string
  designation_id?: string | null
  grade_id?: string | null
  job_level_id?: string | null
  location_id?: string | null
}

/** Correction of wrongly recorded data; changed fields only. */
export interface AssignmentCorrectionBody {
  version: number
  reason: string
  assignment_type?: AssignmentType
  org_unit_id?: string
  designation_id?: string | null
  grade_id?: string | null
  job_level_id?: string | null
  location_id?: string | null
  effective_from?: string | null
  effective_to?: string | null
}

export interface AssignmentEndBody {
  version: number
  effective_to: string
  reason: string | null
}

export interface RecordEndBody {
  effective_to: string
  reason: string | null
}

export interface RoleAssignBody {
  functional_role_id: string
  kind: RoleRecordKind
  effective_from: string
  effective_to: string | null
  reason: string | null
}

export interface ResponsibilityAssignBody {
  responsibility_id: string
  context_unit_id: string | null
  context_location_id: string | null
  effective_from: string
  effective_to: string | null
  reason: string | null
}

/** The relationship type is never sent: the server defaults to LINE_MANAGER. */
export interface ManagerSetBody {
  manager_id: string
  effective_from: string
  reason: string | null
}

export interface AccountLinkBody {
  user_public_id: string
  reason: string | null
}

export interface EmployeeWarning {
  code: string
  message: string
}

export interface AssignmentWrite {
  assignment: Assignment
  warnings: EmployeeWarning[]
}

export function isEmploymentStatus(value: string): value is EmploymentStatus {
  return (EMPLOYMENT_STATUSES as readonly string[]).includes(value)
}

export function isStatusFilter(value: string | null): value is StatusFilter {
  return value !== null && (STATUS_FILTERS as readonly string[]).includes(value)
}

export function isDataQualityCheck(value: string | null): value is DataQualityCheck {
  return value !== null && (DATA_QUALITY_CHECKS as readonly string[]).includes(value)
}

/**
 * Employee audit event codes (LMS_Backend/app/services/audit_service.py) mapped to
 * translation keys under `emp.history.events`. Unknown codes are shown as sent.
 */
export const EMPLOYEE_EVENT_TYPES = [
  ['employee.created', 'employeeCreated'],
  ['employee.corrected', 'employeeCorrected'],
  ['employee.status_changed', 'statusChanged'],
  ['employee_assignment.created', 'assignmentCreated'],
  ['employee_assignment.changed', 'assignmentChanged'],
  ['employee_assignment.ended', 'assignmentEnded'],
  ['employee_assignment.corrected', 'assignmentCorrected'],
  ['employee_functional_role.assigned', 'roleAssigned'],
  ['employee_functional_role.excluded', 'roleExcluded'],
  ['employee_functional_role.ended', 'roleEnded'],
  ['employee_responsibility.assigned', 'responsibilityAssigned'],
  ['employee_responsibility.ended', 'responsibilityEnded'],
  ['reporting_relationship.created', 'reportingCreated'],
  ['reporting_relationship.ended', 'reportingEnded'],
  ['employee_account.linked', 'accountLinked'],
  ['employee_account.unlinked', 'accountUnlinked'],
] as const

export type EmployeeEventLabel = (typeof EMPLOYEE_EVENT_TYPES)[number][1]

const EMPLOYEE_EVENT_LABELS: ReadonlyMap<string, EmployeeEventLabel> = new Map(EMPLOYEE_EVENT_TYPES)

export function employeeEventLabel(code: string): EmployeeEventLabel | undefined {
  return EMPLOYEE_EVENT_LABELS.get(code)
}
