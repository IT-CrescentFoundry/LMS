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
