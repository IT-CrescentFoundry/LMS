import type { RouteObject } from 'react-router'

import { AuditLogPage } from '../../features/admin/AuditLogPage'
import { UsersPage } from '../../features/admin/UsersPage'
import { ChangePasswordPage } from '../../features/auth/ChangePasswordPage'
import { LoginPage } from '../../features/auth/LoginPage'
import { PERMISSIONS } from '../../features/auth/permissions'
import { PublicOnlyRoute, RequireAuth, RequirePermission } from '../../features/auth/RouteGuards'
import { CHANGE_PASSWORD_PATH, LOGIN_PATH } from '../../features/auth/safeRedirect'
import { DashboardPage } from '../../features/dashboard/DashboardPage'
import { NotFoundPage } from '../../features/errors/NotFoundPage'
import { RouteErrorPage } from '../../features/errors/RouteErrorPage'
import { AppLayout } from '../../layouts/AppLayout'
import { AuthLayout } from '../../layouts/AuthLayout'

/**
 * Route table. Shared by the browser router and by tests (memory router).
 *
 * Everything except the sign-in page requires a session (RequireAuth).
 * Admin pages additionally check a permission; the API enforces the same
 * permission on every request, so these guards are a UX layer only.
 */
export const routes: RouteObject[] = [
  {
    errorElement: <RouteErrorPage />,
    children: [
      {
        path: LOGIN_PATH,
        element: (
          <PublicOnlyRoute>
            <AuthLayout>
              <LoginPage />
            </AuthLayout>
          </PublicOnlyRoute>
        ),
      },
      {
        element: <RequireAuth />,
        children: [
          {
            path: CHANGE_PASSWORD_PATH,
            element: (
              <AuthLayout>
                <ChangePasswordPage />
              </AuthLayout>
            ),
          },
          {
            path: '/',
            element: <AppLayout />,
            children: [
              { index: true, element: <DashboardPage /> },
              {
                path: 'admin/users',
                element: (
                  <RequirePermission permission={PERMISSIONS.USER_ACCOUNTS_VIEW}>
                    <UsersPage />
                  </RequirePermission>
                ),
              },
              {
                path: 'admin/audit-log',
                element: (
                  <RequirePermission permission={PERMISSIONS.AUDIT_VIEW}>
                    <AuditLogPage />
                  </RequirePermission>
                ),
              },
              { path: '*', element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]
