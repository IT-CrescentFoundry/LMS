import { ApiError } from '../../lib/apiClient'

/**
 * Backend error codes of the employee API (docs/architecture/API_REFERENCE.md
 * section 9), plus shared codes the employee screens can receive. Every code is
 * translated under `emp.errors.codes`; the backend's English message is never
 * shown. An unknown code is still shown by name with the request reference, never
 * replaced by a generic message.
 */
export const EMPLOYEE_ERROR_CODES = [
  // 404
  'employee_not_found',
  'assignment_not_found',
  'role_assignment_not_found',
  'responsibility_record_not_found',
  'reporting_relationship_not_found',
  'reporting_type_not_found',
  'manager_not_found',
  'user_not_found',
  'org_unit_not_found',
  'designation_not_found',
  'grade_not_found',
  'level_not_found',
  'location_not_found',
  'functional_role_not_found',
  'responsibility_not_found',
  'not_found',
  // 409
  'employee_code_taken',
  'open_records_on_separation',
  'primary_overlap',
  'assignment_overlap',
  'assignment_already_ended',
  'record_already_ended',
  'role_assignment_overlap',
  'responsibility_overlap',
  'manager_overlap',
  'reporting_cycle',
  'later_change_exists',
  'account_already_linked',
  'employee_has_active_account',
  'account_not_linked',
  'version_conflict',
  // 422
  'invalid_employee_code',
  'invalid_employment_dates',
  'separation_date_required',
  'separation_date_not_allowed',
  'outside_employment_period',
  'assignment_start_required',
  'unit_required',
  'unit_not_active',
  'reference_inactive',
  'change_date_invalid',
  'invalid_period',
  'functional_role_inactive',
  'responsibility_inactive',
  'location_inactive',
  'self_reporting',
  'manager_separated',
  'reporting_type_inactive',
  'invalid_check',
  'no_change',
  'invalid_cursor',
  'validation_error',
  // 403
  'forbidden',
  'self_modification_forbidden',
  'insufficient_privilege',
  'password_change_required',
] as const
export type EmployeeErrorCode = (typeof EMPLOYEE_ERROR_CODES)[number]

/** `details[].type` of `409 open_records_on_separation`. */
export const SEPARATION_BLOCKER_TYPES = [
  'open_assignment',
  'open_functional_role',
  'open_responsibility',
  'open_reporting_line',
  'open_direct_report',
  'starts_after_separation',
] as const
export type SeparationBlockerType = (typeof SEPARATION_BLOCKER_TYPES)[number]

export const EMPLOYEE_WARNING_CODES = ['unit_type_not_assignable'] as const
export type EmployeeWarningCode = (typeof EMPLOYEE_WARNING_CODES)[number]

export function isEmployeeErrorCode(value: string | undefined): value is EmployeeErrorCode {
  return (EMPLOYEE_ERROR_CODES as readonly (string | undefined)[]).includes(value)
}

export function isSeparationBlockerType(value: string): value is SeparationBlockerType {
  return (SEPARATION_BLOCKER_TYPES as readonly string[]).includes(value)
}

export function isEmployeeWarningCode(value: string): value is EmployeeWarningCode {
  return (EMPLOYEE_WARNING_CODES as readonly string[]).includes(value)
}

export interface SeparationBlocker {
  /** `other` for a type this version of the UI does not know (shown by name). */
  type: SeparationBlockerType | 'other'
  rawType: string
  /** What the API names: a unit, role or responsibility code, or an employee code. */
  label: string
}

export type EmployeeErrorDescription =
  | { kind: 'code'; code: EmployeeErrorCode; blockers: SeparationBlocker[]; requestId?: string }
  | { kind: 'unknown_code'; code: string; requestId?: string }
  | { kind: 'network' }
  | { kind: 'generic'; requestId?: string }

/** Classifies a failed request for display. */
export function describeEmployeeError(error: unknown): EmployeeErrorDescription {
  if (!(error instanceof ApiError)) return { kind: 'generic' }
  if (error.kind === 'network' || error.kind === 'timeout') return { kind: 'network' }
  if (isEmployeeErrorCode(error.code)) {
    const blockers =
      error.code === 'open_records_on_separation'
        ? error.details.map((detail) => ({
            type: isSeparationBlockerType(detail.type) ? detail.type : ('other' as const),
            rawType: detail.type,
            label: detail.location[detail.location.length - 1] ?? '',
          }))
        : []
    return { kind: 'code', code: error.code, blockers, requestId: error.requestId }
  }
  if (error.code) return { kind: 'unknown_code', code: error.code, requestId: error.requestId }
  return { kind: 'generic', requestId: error.requestId }
}

/** How a field-level validation problem is explained (translated by the UI). */
export type FieldIssueKind = 'required' | 'tooLong' | 'format' | 'date' | 'invalid'

function issueKind(type: string): FieldIssueKind {
  if (type === 'missing') return 'required'
  if (type === 'string_too_long' || type === 'too_long') return 'tooLong'
  if (type === 'string_pattern_mismatch') return 'format'
  if (type.startsWith('date')) return 'date'
  return 'invalid'
}

/**
 * Request-body fields named by a `422 validation_error` (`location` is
 * `['body', field, ...]`). Anything without a reliable field location is left
 * to the form-level message, which is always shown as well.
 */
export function serverFieldIssues(error: unknown): Map<string, FieldIssueKind> {
  const issues = new Map<string, FieldIssueKind>()
  if (!(error instanceof ApiError) || error.code !== 'validation_error') return issues
  for (const detail of error.details) {
    const [where, field] = detail.location
    if (where === 'body' && typeof field === 'string' && field !== '' && !issues.has(field)) {
      issues.set(field, issueKind(detail.type))
    }
  }
  return issues
}
