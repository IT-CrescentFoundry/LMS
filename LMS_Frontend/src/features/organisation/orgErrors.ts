import { ApiError } from '../../lib/apiClient'

/**
 * Backend error codes of the organisation API (docs/architecture/API_REFERENCE.md
 * sections 7-8). Codes are translated; the backend's English message is never shown.
 */
export const ORG_ERROR_CODES = [
  'version_conflict',
  'not_found',
  'unit_type_not_found',
  'org_unit_not_found',
  'location_not_found',
  'job_family_not_found',
  'grade_not_found',
  'job_level_not_found',
  'designation_not_found',
  'functional_role_not_found',
  'responsibility_not_found',
  'mapping_not_found',
  'unit_type_code_taken',
  'unit_code_taken',
  'location_code_taken',
  'job_family_code_taken',
  'grade_code_taken',
  'job_level_code_taken',
  'designation_code_taken',
  'functional_role_code_taken',
  'responsibility_code_taken',
  'sibling_name_taken',
  'later_change_exists',
  'unit_has_dependants',
  'unit_already_closed',
  'unit_not_closed',
  'parent_closed',
  'location_in_use',
  'designation_in_use',
  'functional_role_in_use',
  'mapping_overlap',
  'mapping_already_ended',
  'invalid_code',
  'invalid_period',
  'parent_not_active',
  'type_rule_violation',
  'hierarchy_cycle',
  'move_date_invalid',
  'no_change',
  'period_conflict',
  'unit_type_inactive',
  'location_inactive',
  'invalid_time_zone',
  'job_family_cycle',
  'job_family_inactive',
  'designation_inactive',
  'functional_role_inactive',
  'unit_closed',
  'unit_not_active',
  'invalid_cursor',
  'validation_error',
  'forbidden',
  'password_change_required',
] as const
export type OrgErrorCode = (typeof ORG_ERROR_CODES)[number]

export const BLOCKER_TYPES = [
  'active_child',
  'owned_functional_role',
  'scoped_mapping',
  // Stage C3: employee records in the unit that continue after the closure date
  'employee_assignment',
  'employee_responsibility',
] as const
export type BlockerType = (typeof BLOCKER_TYPES)[number]

export const WARNING_CODES = ['type_rule_advisory'] as const
export type WarningCode = (typeof WARNING_CODES)[number]

export function isOrgErrorCode(value: string | undefined): value is OrgErrorCode {
  return (ORG_ERROR_CODES as readonly (string | undefined)[]).includes(value)
}

export function isBlockerType(value: string): value is BlockerType {
  return (BLOCKER_TYPES as readonly string[]).includes(value)
}

export function isWarningCode(value: string): value is WarningCode {
  return (WARNING_CODES as readonly string[]).includes(value)
}

export interface Blocker {
  type: BlockerType | 'other'
  /** The dependant's code (child unit or functional role), when the API names it. */
  label: string
}

export type OrgErrorDescription =
  | { kind: 'code'; code: OrgErrorCode; blockers: Blocker[] }
  | { kind: 'network' }
  | { kind: 'generic'; requestId?: string }

/** Classifies a failed change for display. */
export function describeOrgError(error: unknown): OrgErrorDescription {
  if (!(error instanceof ApiError)) return { kind: 'generic' }
  if (error.kind === 'network' || error.kind === 'timeout') return { kind: 'network' }
  if (isOrgErrorCode(error.code)) {
    const blockers =
      error.code === 'unit_has_dependants'
        ? error.details.map((detail) => ({
            type: isBlockerType(detail.type) ? detail.type : ('other' as const),
            label: detail.location[1] ?? '',
          }))
        : []
    return { kind: 'code', code: error.code, blockers }
  }
  return { kind: 'generic', requestId: error.requestId }
}

export function isVersionConflict(error: unknown): boolean {
  return error instanceof ApiError && error.code === 'version_conflict'
}
