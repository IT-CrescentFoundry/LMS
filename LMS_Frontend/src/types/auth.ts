/**
 * Mirrors the backend schemas in LMS_Backend/app/schemas/auth.py.
 *
 * Deliberately absent: password hashes, session tokens and token hashes (the
 * backend never sends them). The CSRF token is also not part of these types:
 * it lives only inside `src/lib/apiClient.ts`.
 */

export interface CurrentUser {
  public_id: string
  login_id: string
  display_name: string
  email: string | null
  status: string
  password_must_change: boolean
  /** Access-role codes, e.g. "hr_admin". Display only - never used for access decisions. */
  roles: string[]
  /** Permission codes, e.g. "audit.view". The UI gates screens on these. */
  permissions: string[]
}

export type AuthSession =
  | { authenticated: false }
  | {
      authenticated: true
      user: CurrentUser
      idle_expires_at: string
      absolute_expires_at: string
    }

export type AuthenticatedSession = Extract<AuthSession, { authenticated: true }>

/** Access roles seeded by the backend (labels are translated in the UI). */
export const ROLE_CODES = ['employee', 'supervisor', 'hod', 'sme', 'hr_admin', 'super_admin'] as const
export type RoleCode = (typeof ROLE_CODES)[number]

export function isRoleCode(value: string): value is RoleCode {
  return (ROLE_CODES as readonly string[]).includes(value)
}

/** Password-policy issue types returned in `error.details[].type`. */
export const PASSWORD_ISSUES = [
  'too_short',
  'too_long',
  'contains_login_id',
  'repeated_character',
  'too_common',
  'same_as_current',
] as const
export type PasswordIssue = (typeof PASSWORD_ISSUES)[number]

export function isPasswordIssue(value: string): value is PasswordIssue {
  return (PASSWORD_ISSUES as readonly string[]).includes(value)
}
