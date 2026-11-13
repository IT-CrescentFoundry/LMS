import { isRecord } from '../../lib/apiClient'

export const LOGIN_PATH = '/login'
export const CHANGE_PASSWORD_PATH = '/change-password'

/**
 * Where to go after signing in. The target comes only from router state set
 * by our own guards (never from the URL), and must be an internal path, so a
 * crafted link cannot turn the sign-in page into an open redirect.
 */
export function safeRedirectTarget(state: unknown): string {
  const from = isRecord(state) ? state.from : undefined
  if (typeof from !== 'string') return '/'
  if (!from.startsWith('/') || from.startsWith('//') || from.startsWith('/\\')) return '/'
  const pathname = from.split(/[?#]/, 1)[0]
  if (pathname === LOGIN_PATH) return '/'
  return from
}
