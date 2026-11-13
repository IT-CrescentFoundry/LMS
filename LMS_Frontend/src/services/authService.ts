import { apiRequest, ApiError, parseNoContent, setCsrfToken } from '../lib/apiClient'
import {
  expectBoolean,
  expectDateString,
  expectNullableString,
  expectRecord,
  expectString,
  expectStringArray,
} from '../lib/parse'
import type { AuthenticatedSession, AuthSession, CurrentUser } from '../types/auth'

export function parseCurrentUser(data: unknown): CurrentUser {
  const record = expectRecord(data, 'user')
  return {
    public_id: expectString(record, 'public_id'),
    login_id: expectString(record, 'login_id'),
    display_name: expectString(record, 'display_name'),
    email: expectNullableString(record, 'email'),
    status: expectString(record, 'status'),
    password_must_change: expectBoolean(record, 'password_must_change'),
    roles: expectStringArray(record, 'roles'),
    permissions: expectStringArray(record, 'permissions'),
  }
}

interface ParsedSession {
  session: AuthSession
  csrfToken: string | null
}

/** Parses `SessionResponse`. The CSRF token is returned separately, never cached. */
export function parseSessionResponse(data: unknown): ParsedSession {
  const record = expectRecord(data, 'session')
  if (!expectBoolean(record, 'authenticated')) {
    return { session: { authenticated: false }, csrfToken: null }
  }
  return {
    session: {
      authenticated: true,
      user: parseCurrentUser(record.user),
      idle_expires_at: expectDateString(record, 'idle_expires_at'),
      absolute_expires_at: expectDateString(record, 'absolute_expires_at'),
    },
    csrfToken: expectString(record, 'csrf_token'),
  }
}

function parseAuthenticatedSession(data: unknown): ParsedSession & { session: AuthenticatedSession } {
  const parsed = parseSessionResponse(data)
  if (!parsed.session.authenticated) throw new TypeError('expected an authenticated session')
  return { session: parsed.session, csrfToken: parsed.csrfToken }
}

/**
 * Authentication API (LMS_Backend/app/api/routes/auth.py).
 * Each call that returns a session stores its CSRF token in memory before
 * resolving, so the next state-changing request can use it immediately.
 */
export const authService = {
  /** Public; restores the session after a reload. Never extends the idle window. */
  async getSession(signal?: AbortSignal): Promise<AuthSession> {
    const { session, csrfToken } = await apiRequest('/auth/session', {
      parse: parseSessionResponse,
      signal,
      authRecovery: false,
    })
    setCsrfToken(csrfToken)
    return session
  },

  /** No CSRF token is sent: the backend protects login with its trusted-origin check. */
  async login(loginId: string, password: string): Promise<AuthenticatedSession> {
    const { session, csrfToken } = await apiRequest('/auth/login', {
      method: 'POST',
      body: { login_id: loginId, password },
      parse: parseAuthenticatedSession,
      csrf: false,
      authRecovery: false,
    })
    setCsrfToken(csrfToken)
    return session
  },

  /** Revokes the session server-side. A 401 means it had already ended. */
  async logout(): Promise<void> {
    try {
      await apiRequest('/auth/logout', {
        method: 'POST',
        parse: parseNoContent,
        authRecovery: false,
      })
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) throw error
    }
    setCsrfToken(null)
  },

  /** Rotates the session: the response carries a new CSRF token. */
  async changePassword(currentPassword: string, newPassword: string): Promise<AuthenticatedSession> {
    const { session, csrfToken } = await apiRequest('/auth/password', {
      method: 'POST',
      body: { current_password: currentPassword, new_password: newPassword },
      parse: parseAuthenticatedSession,
    })
    setCsrfToken(csrfToken)
    return session
  },
}
