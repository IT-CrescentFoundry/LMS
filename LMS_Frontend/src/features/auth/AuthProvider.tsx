import { useQuery, useQueryClient, type Query } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { setAuthHandlers, setCsrfToken } from '../../lib/apiClient'
import { authService } from '../../services/authService'
import type { AuthSession } from '../../types/auth'
import {
  AuthContext,
  authQueryKeys,
  type AuthContextValue,
  type AuthStatus,
  type SignedOutReason,
} from './authContext'

/** Re-check the session this long after the server says it expires. */
const EXPIRY_GRACE_MS = 5_000
/** Never re-check more often than this (guards against clock skew loops). */
const MIN_RECHECK_MS = 15_000
const SESSION_STALE_MS = 60_000

const ANONYMOUS: AuthSession = { authenticated: false }

/** Everything cached for the signed-in user (i.e. all but session and health). */
function isPrivateQuery(query: Query): boolean {
  const scope = query.queryKey[0]
  return scope !== 'auth' && scope !== 'health'
}

/**
 * Owns the client-side view of the server session.
 *
 * - The session itself lives in an HttpOnly cookie that JavaScript cannot read.
 * - `GET /auth/session` restores the user, permissions and CSRF token after a
 *   reload; it is re-checked on window focus and when the server-side expiry
 *   time passes (that check never extends the idle window).
 * - Signing out or an ended session purges every cached query that may hold
 *   another user's data.
 * The server remains the authority: these checks only keep the UI in step.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [signedOutReason, setSignedOutReason] = useState<SignedOutReason>(null)

  const purgePrivateData = useCallback(() => {
    void queryClient.cancelQueries({ predicate: isPrivateQuery })
    queryClient.removeQueries({ predicate: isPrivateQuery })
  }, [queryClient])

  const endSession = useCallback(
    (reason: Exclude<SignedOutReason, null>) => {
      setCsrfToken(null)
      purgePrivateData()
      queryClient.setQueryData<AuthSession>(authQueryKeys.session, ANONYMOUS)
      setSignedOutReason(reason)
    },
    [purgePrivateData, queryClient],
  )

  const fetchSession = useCallback(
    async (signal?: AbortSignal): Promise<AuthSession> => {
      const previous = queryClient.getQueryData<AuthSession>(authQueryKeys.session)
      const next = await authService.getSession(signal)
      if (previous?.authenticated) {
        if (!next.authenticated) {
          purgePrivateData()
          setSignedOutReason('expired')
        } else if (next.user.public_id !== previous.user.public_id) {
          purgePrivateData() // another tab signed in as someone else
        }
      }
      return next
    },
    [purgePrivateData, queryClient],
  )

  const sessionQuery = useQuery({
    queryKey: authQueryKeys.session,
    queryFn: ({ signal }) => fetchSession(signal),
    staleTime: SESSION_STALE_MS,
    refetchOnWindowFocus: true,
  })
  const { data: session, dataUpdatedAt, refetch, isError, isFetching } = sessionQuery

  useEffect(
    () =>
      setAuthHandlers({
        onUnauthenticated: () => {
          const current = queryClient.getQueryData<AuthSession>(authQueryKeys.session)
          if (current?.authenticated) endSession('expired')
        },
        refreshSession: async () => {
          await queryClient.fetchQuery({
            queryKey: authQueryKeys.session,
            queryFn: ({ signal }) => fetchSession(signal),
            staleTime: 0,
          })
        },
      }),
    [endSession, fetchSession, queryClient],
  )

  // Re-check when the server-side session is due to expire. If other requests
  // extended the idle window meanwhile, the re-check returns the new expiry and
  // this effect reschedules (dataUpdatedAt changes on every successful fetch).
  useEffect(() => {
    if (!session?.authenticated) return undefined
    const expiresAt = Math.min(
      Date.parse(session.idle_expires_at),
      Date.parse(session.absolute_expires_at),
    )
    const delay = Math.max(MIN_RECHECK_MS, expiresAt - Date.now() + EXPIRY_GRACE_MS)
    const timer = window.setTimeout(() => void refetch(), delay)
    return () => window.clearTimeout(timer)
  }, [session, dataUpdatedAt, refetch])

  const signIn = useCallback(
    async (loginId: string, password: string) => {
      const next = await authService.login(loginId, password)
      purgePrivateData()
      queryClient.setQueryData<AuthSession>(authQueryKeys.session, next)
      setSignedOutReason(null)
    },
    [purgePrivateData, queryClient],
  )

  const signOut = useCallback(async () => {
    await authService.logout()
    endSession('signed_out')
  }, [endSession])

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      const next = await authService.changePassword(currentPassword, newPassword)
      queryClient.setQueryData<AuthSession>(authQueryKeys.session, next)
    },
    [queryClient],
  )

  const refresh = useCallback(async () => {
    await refetch()
  }, [refetch])

  let status: AuthStatus
  if (session) status = session.authenticated ? 'authenticated' : 'anonymous'
  else if (isError) status = 'unavailable'
  else status = 'loading'

  const user = session?.authenticated ? session.user : null

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      signedOutReason,
      isRefreshing: isFetching,
      signIn,
      signOut,
      changePassword,
      refresh,
    }),
    [status, user, signedOutReason, isFetching, signIn, signOut, changePassword, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
