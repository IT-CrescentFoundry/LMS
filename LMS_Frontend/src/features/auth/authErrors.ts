import { ApiError } from '../../lib/apiClient'

export type ApiErrorMessageKey =
  | 'auth.errors.invalidCredentials'
  | 'auth.errors.tooManyAttempts'
  | 'auth.errors.accountInactive'
  | 'auth.errors.originNotAllowed'
  | 'auth.errors.employeeHasActiveAccount'
  | 'auth.errors.network'
  | 'auth.errors.generic'

export interface DescribedError {
  key: ApiErrorMessageKey
  /** Shown for unexpected errors so support can find the server log entry. */
  requestId?: string
}

/**
 * Maps an API failure to a translated message. Backend error CODES are
 * translated; the backend's English `message` is never shown to users.
 */
export function describeApiError(error: unknown): DescribedError {
  if (!(error instanceof ApiError)) return { key: 'auth.errors.generic' }
  if (error.kind === 'network' || error.kind === 'timeout') return { key: 'auth.errors.network' }
  switch (error.code) {
    case 'invalid_credentials':
      return { key: 'auth.errors.invalidCredentials' }
    case 'too_many_attempts':
      return { key: 'auth.errors.tooManyAttempts' }
    case 'account_inactive':
      return { key: 'auth.errors.accountInactive' }
    case 'origin_not_allowed':
      return { key: 'auth.errors.originNotAllowed' }
    case 'employee_has_active_account':
      // Stage C3: re-activating an account while its employee has another active one.
      return { key: 'auth.errors.employeeHasActiveAccount' }
    default:
      return { key: 'auth.errors.generic', requestId: error.requestId }
  }
}
