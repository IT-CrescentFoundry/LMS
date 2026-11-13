import { createContext, useContext } from 'react'

import type { CurrentUser } from '../../types/auth'
import { hasPermission, type PermissionCode } from './permissions'

/**
 * - loading:       first session check still running
 * - authenticated: a valid server-side session exists
 * - anonymous:     no session (never signed in, signed out or expired)
 * - unavailable:   the session could not be checked (API unreachable). This is
 *                  NOT treated as signed out.
 */
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous' | 'unavailable'

/** Why the session ended, for the message on the sign-in page. */
export type SignedOutReason = 'expired' | 'signed_out' | null

export interface AuthContextValue {
  status: AuthStatus
  user: CurrentUser | null
  signedOutReason: SignedOutReason
  /** True while the session is being re-checked. */
  isRefreshing: boolean
  signIn: (loginId: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  refresh: () => Promise<void>
}

export const authQueryKeys = {
  session: ['auth', 'session'] as const,
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (value === null) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}

/** UI visibility only - the backend enforces every permission itself. */
export function useHasPermission(permission: PermissionCode): boolean {
  return hasPermission(useAuth().user, permission)
}
