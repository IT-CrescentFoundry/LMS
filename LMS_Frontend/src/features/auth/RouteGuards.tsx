import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { ForbiddenPage } from '../errors/ForbiddenPage'
import { useAuth, useHasPermission } from './authContext'
import { hasAnyPermission, type PermissionCode } from './permissions'
import { CHANGE_PASSWORD_PATH, LOGIN_PATH, safeRedirectTarget } from './safeRedirect'
import { SessionLoadingScreen, SessionUnavailableScreen } from './SessionScreens'

/**
 * Layout route for everything that needs a signed-in user. Anonymous visitors
 * are sent to the sign-in page (remembering where they were going, unless they
 * just signed out); users who must change their password are held on that page.
 */
export function RequireAuth() {
  const { status, user, signedOutReason, refresh, isRefreshing } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <SessionLoadingScreen />
  if (status === 'unavailable') {
    return <SessionUnavailableScreen onRetry={() => void refresh()} isRetrying={isRefreshing} />
  }
  if (user === null) {
    const state =
      signedOutReason === 'signed_out'
        ? undefined
        : { from: `${location.pathname}${location.search}${location.hash}` }
    return <Navigate to={LOGIN_PATH} replace state={state} />
  }
  if (user.password_must_change && location.pathname !== CHANGE_PASSWORD_PATH) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />
  }
  return <Outlet />
}

/** Wraps the sign-in page: signed-in users continue to where they were going. */
export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <SessionLoadingScreen />
  if (user !== null) {
    const target = user.password_must_change
      ? CHANGE_PASSWORD_PATH
      : safeRedirectTarget(location.state)
    return <Navigate to={target} replace />
  }
  return children
}

/**
 * Shows a 403 page instead of `children` when the user lacks `permission`.
 * This only avoids showing a screen that would fail: the API enforces the
 * permission on every request regardless.
 */
export function RequirePermission({
  permission,
  children,
}: {
  permission: PermissionCode
  children: ReactNode
}) {
  return useHasPermission(permission) ? children : <ForbiddenPage />
}

/** Like RequirePermission, but any one of `permissions` is enough. */
export function RequireAnyPermission({
  permissions,
  children,
}: {
  permissions: readonly PermissionCode[]
  children: ReactNode
}) {
  const { user } = useAuth()
  return hasAnyPermission(user, permissions) ? children : <ForbiddenPage />
}
