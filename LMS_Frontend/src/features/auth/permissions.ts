import type { CurrentUser } from '../../types/auth'

/**
 * Permission codes, mirroring `Permission` in
 * LMS_Backend/app/services/identity/permissions.py.
 *
 * The UI uses them only to decide what to SHOW. Every API endpoint enforces
 * its own permission on the server; hiding a link or a page is a convenience,
 * never a security boundary. Role names are never compared in the UI.
 */
export const PERMISSIONS = {
  USER_ACCOUNTS_VIEW: 'user_accounts.view',
  USER_ACCOUNTS_MANAGE: 'user_accounts.manage',
  USER_SESSIONS_REVOKE: 'user_sessions.revoke',
  USER_ROLES_ASSIGN: 'user_roles.assign',
  USER_ROLES_ASSIGN_ADMIN: 'user_roles.assign_admin',
  ACCESS_ROLES_VIEW: 'access_roles.view',
  ACCESS_ROLES_MANAGE: 'access_roles.manage',
  AUDIT_VIEW: 'audit.view',
  // Stage C1 - organisation structure and reference data
  ORGANISATION_VIEW: 'organisation.view',
  ORGANISATION_MANAGE: 'organisation.manage',
  DESIGNATIONS_MANAGE: 'designations.manage',
  FUNCTIONAL_ROLES_MANAGE: 'functional_roles.manage',
  RESPONSIBILITIES_MANAGE: 'responsibilities.manage',
  // Stage C3 - employee master (global grants only until C4)
  EMPLOYEES_VIEW: 'employees.view',
  EMPLOYEES_HISTORY_VIEW: 'employees.history.view',
  EMPLOYEES_MANAGE: 'employees.manage',
  REPORTING_LINES_MANAGE: 'reporting_lines.manage',
  // Stage D - Excel imports (migration 0010; HR Admin and Super Admin)
  IMPORTS_VIEW: 'imports.view',
  IMPORTS_EMPLOYEES_RUN: 'imports.employees.run',
  IMPORTS_EMPLOYEES_COMMIT: 'imports.employees.commit',
  IMPORTS_MAPPINGS_MANAGE: 'imports.mappings.manage',
  // Organisation import profile (migration 0011)
  IMPORTS_ORGANISATION_RUN: 'imports.organisation.run',
  IMPORTS_ORGANISATION_COMMIT: 'imports.organisation.commit',
  // First release (migration 0011): training register, competency, skill matrix
  TRAINING_RECORDS_VIEW: 'training.records.view',
  COMPETENCY_VIEW: 'competency.view',
  COMPETENCY_MANAGE: 'competency.manage',
  COMPETENCY_ASSESS: 'competency.assess',
  LEARNING_OWN_VIEW: 'learning.own.view',
  CERTIFICATES_OWN_VIEW: 'certificates.own.view',
  TRAINING_REQUESTS_SUBMIT: 'training_requests.submit',
  TEAM_LEARNING_VIEW: 'team.learning.view',
  LEARNING_CONTENT_MANAGE: 'learning_content.manage',
  LEARNING_CONTENT_REVIEW: 'learning_content.review',
  LEARNING_CONTENT_PUBLISH: 'learning_content.publish',
  TRAINING_EVENTS_MANAGE: 'training_events.manage',
  SETTINGS_MANAGE: 'settings.manage',
} as const

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

export function hasPermission(
  user: CurrentUser | null | undefined,
  permission: PermissionCode,
): boolean {
  return user?.permissions.includes(permission) ?? false
}

/** True when the user holds at least one of `permissions` (UI visibility only). */
export function hasAnyPermission(
  user: CurrentUser | null | undefined,
  permissions: readonly PermissionCode[],
): boolean {
  return permissions.some((permission) => hasPermission(user, permission))
}

/** Any of these lets a user open the training register and calendar (scope decided by the server). */
export const TRAINING_VIEW_PERMISSIONS: readonly PermissionCode[] = [
  PERMISSIONS.TRAINING_RECORDS_VIEW,
  PERMISSIONS.TEAM_LEARNING_VIEW,
  PERMISSIONS.LEARNING_OWN_VIEW,
  PERMISSIONS.TRAINING_EVENTS_MANAGE,
]

/** Any of these lets a user open the skill matrix and competency library. */
export const COMPETENCY_VIEW_PERMISSIONS: readonly PermissionCode[] = [
  PERMISSIONS.COMPETENCY_VIEW,
  PERMISSIONS.COMPETENCY_MANAGE,
  PERMISSIONS.TEAM_LEARNING_VIEW,
  PERMISSIONS.LEARNING_OWN_VIEW,
]

/** Running any import profile (`imports.<profile>.run`). */
export const IMPORT_RUN_PERMISSIONS: readonly PermissionCode[] = [
  PERMISSIONS.IMPORTS_EMPLOYEES_RUN,
  PERMISSIONS.IMPORTS_ORGANISATION_RUN,
]
