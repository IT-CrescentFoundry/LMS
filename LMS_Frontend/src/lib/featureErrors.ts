/** Classification of API failures for the first-release feature pages. */

import { ApiError } from './apiClient'

/** The server's stable error code, when the failure came from the API. */
export function apiErrorCode(error: unknown): string | undefined {
  return error instanceof ApiError ? error.code : undefined
}

/** True while the feature's database migration (0011) has not been applied. */
export function isSchemaPending(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503 && error.code === 'schema_migration_pending'
}

/**
 * True for the documented `404 employee_not_linked` answer: the signed-in account
 * has no employee record. Other 404s are real errors and are not matched.
 */
export function isEmployeeNotLinked(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404 && error.code === 'employee_not_linked'
}

/** True for answers that mean "not for you / not here" (widgets hide themselves). */
export function isHiddenError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403 || error.status === 404)
}
