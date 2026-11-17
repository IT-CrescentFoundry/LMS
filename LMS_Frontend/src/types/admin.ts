/**
 * Mirrors the read-only administration schemas in
 * LMS_Backend/app/schemas/{users,audit,pagination}.py.
 */

export const ACCOUNT_STATUSES = ['pending_activation', 'active', 'suspended', 'disabled'] as const
export type AccountStatus = (typeof ACCOUNT_STATUSES)[number]

export const AUDIT_OUTCOMES = ['success', 'failure', 'denied'] as const
export type AuditOutcome = (typeof AUDIT_OUTCOMES)[number]

export function isAccountStatus(value: string): value is AccountStatus {
  return (ACCOUNT_STATUSES as readonly string[]).includes(value)
}

export function isAuditOutcome(value: string): value is AuditOutcome {
  return (AUDIT_OUTCOMES as readonly string[]).includes(value)
}

export const AUDIT_TARGET_TYPES = [
  'user_account',
  'user_session',
  'access_role',
  'import_job',
  'import_value_mapping',
] as const
export type AuditTargetType = (typeof AUDIT_TARGET_TYPES)[number]

export function isAuditTargetType(value: string): value is AuditTargetType {
  return (AUDIT_TARGET_TYPES as readonly string[]).includes(value)
}

/**
 * Audit event codes (LMS_Backend/app/services/audit_service.py) mapped to
 * translation keys under `audit.events`. Unknown codes are shown as-is.
 */
export const AUDIT_EVENT_TYPES = [
  ['auth.login.succeeded', 'loginSucceeded'],
  ['auth.login.failed', 'loginFailed'],
  ['auth.login.throttled', 'loginThrottled'],
  ['auth.login.denied_inactive', 'loginDeniedInactive'],
  ['auth.logout', 'logout'],
  ['auth.password.changed', 'passwordChanged'],
  ['auth.password.change_failed', 'passwordChangeFailed'],
  ['user_account.created', 'accountCreated'],
  ['user_account.updated', 'accountUpdated'],
  ['user_account.activated', 'accountActivated'],
  ['user_account.suspended', 'accountSuspended'],
  ['user_account.disabled', 'accountDisabled'],
  ['user_account.password_reset', 'accountPasswordReset'],
  ['user_session.revoked', 'sessionRevoked'],
  ['user_session.revoked_all', 'sessionsRevokedAll'],
  ['access_role.granted', 'roleGranted'],
  ['access_role.revoked', 'roleRevoked'],
  ['access_role.permission_granted', 'rolePermissionGranted'],
  ['access_role.permission_revoked', 'rolePermissionRevoked'],
  ['super_admin.bootstrapped', 'superAdminBootstrapped'],
  ['super_admin.granted', 'superAdminGranted'],
  ['super_admin.revoked', 'superAdminRevoked'],
  ['authorization.denied', 'authorizationDenied'],
  ['audit.events.viewed', 'auditViewed'],
  // Stage D - Excel imports
  ['import.job.uploaded', 'importUploaded'],
  ['import.upload.rejected', 'importUploadRejected'],
  ['import.job.mapping_set', 'importMappingSet'],
  ['import.job.validated', 'importValidated'],
  ['import.row.decided', 'importRowDecided'],
  ['import.job.committed', 'importCommitted'],
  ['import.job.commit_failed', 'importCommitFailed'],
  ['import.job.cancelled', 'importCancelled'],
  ['import.job.expired', 'importExpired'],
  ['import.job.validation_abandoned', 'importValidationAbandoned'],
  ['import.mapping.approved', 'importMappingApproved'],
  ['import.mapping.rejected', 'importMappingRejected'],
  ['import.mapping.superseded', 'importMappingSuperseded'],
] as const

export type AuditEventLabel = (typeof AUDIT_EVENT_TYPES)[number][1]

const AUDIT_EVENT_LABELS: ReadonlyMap<string, AuditEventLabel> = new Map(AUDIT_EVENT_TYPES)

export function auditEventLabel(code: string): AuditEventLabel | undefined {
  return AUDIT_EVENT_LABELS.get(code)
}

/** Cursor-paginated list (newest first). `next_cursor` is null on the last page. */
export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

/** The employee record an account is linked to (Stage C3). */
export interface LinkedEmployee {
  public_id: string
  employee_code: string
  full_name: string
}

export interface UserSummary {
  public_id: string
  login_id: string
  display_name: string
  email: string | null
  status: string
  roles: string[]
  last_login_at: string | null
  created_at: string
  /** Null when the account is not linked to an employee record. */
  employee: LinkedEmployee | null
}

export interface AuditActor {
  public_id: string
  login_id: string
  display_name: string
}

export interface AuditEvent {
  event_id: string
  occurred_at: string
  event_type: string
  outcome: string
  actor: AuditActor | null
  target_type: string | null
  target_id: string | null
  request_id: string | null
  source_ip: string | null
  user_agent: string | null
  metadata: Record<string, unknown> | null
}

export interface UserFilters {
  status?: AccountStatus
  q?: string
  /** Stage C3: only accounts with (true) or without (false) an employee link. */
  linked?: boolean
  /** Only accounts the caller may manage (not their own, no permission they lack). */
  manageable?: boolean
}

export interface AuditFilters {
  event_type?: string
  outcome?: AuditOutcome
  /** ISO date-time, inclusive. */
  occurred_from?: string
  /** ISO date-time, exclusive. */
  occurred_to?: string
}
