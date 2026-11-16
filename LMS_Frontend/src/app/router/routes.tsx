import { Outlet, type RouteObject } from 'react-router'

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
import { OrganisationLayout } from '../../features/organisation/OrganisationLayout'
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
              {
                // Organisation area: viewing needs organisation.view; each page
                // shows its management controls only with the matching
                // *.manage permission (the API enforces both).
                path: 'organisation',
                element: (
                  <RequirePermission permission={PERMISSIONS.ORGANISATION_VIEW}>
                    <OrganisationLayout />
                  </RequirePermission>
                ),
                // Pages are loaded on first visit (separate bundles), so users who
                // never open the organisation area never download it.
                children: [
                  {
                    index: true,
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/OrganisationStructurePage'))
                        .OrganisationStructurePage,
                    }),
                  },
                  {
                    path: 'unit-types',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/UnitTypesPage')).UnitTypesPage,
                    }),
                  },
                  {
                    path: 'locations',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/LocationsPage')).LocationsPage,
                    }),
                  },
                  {
                    path: 'job-families',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/JobFamiliesPage')).JobFamiliesPage,
                    }),
                  },
                  {
                    path: 'designations',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/DesignationsPage')).DesignationsPage,
                    }),
                  },
                  {
                    path: 'grades',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/RankedListPage')).GradesPage,
                    }),
                  },
                  {
                    path: 'levels',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/RankedListPage')).LevelsPage,
                    }),
                  },
                  {
                    path: 'functional-roles',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/FunctionalRolesPage'))
                        .FunctionalRolesPage,
                    }),
                  },
                  {
                    path: 'responsibilities',
                    lazy: async () => ({
                      Component: (await import('../../features/organisation/ResponsibilitiesPage'))
                        .ResponsibilitiesPage,
                    }),
                  },
                ],
              },
              {
                // Employee area (Stage C3): viewing needs employees.view; the
                // assignment timeline and history need employees.history.view;
                // changes and the data-quality report need employees.manage (the
                // API enforces all of them). Directory and Data quality share the
                // section-pill shell; profiles have their own header and tabs.
                path: 'employees',
                element: (
                  <RequirePermission permission={PERMISSIONS.EMPLOYEES_VIEW}>
                    <Outlet />
                  </RequirePermission>
                ),
                children: [
                  {
                    lazy: async () => ({
                      Component: (await import('../../features/employees/EmployeesLayout')).EmployeesLayout,
                    }),
                    children: [
                      {
                        index: true,
                        lazy: async () => ({
                          Component: (await import('../../features/employees/EmployeeDirectoryPage'))
                            .EmployeeDirectoryPage,
                        }),
                      },
                      {
                        path: 'data-quality',
                        lazy: async () => {
                          const { DataQualityPage } = await import('../../features/employees/DataQualityPage')
                          return {
                            element: (
                              <RequirePermission permission={PERMISSIONS.EMPLOYEES_MANAGE}>
                                <DataQualityPage />
                              </RequirePermission>
                            ),
                          }
                        },
                      },
                    ],
                  },
                  {
                    path: ':employeeId',
                    lazy: async () => ({
                      Component: (await import('../../features/employees/EmployeeProfileLayout'))
                        .EmployeeProfileLayout,
                    }),
                    children: [
                      {
                        index: true,
                        lazy: async () => ({
                          Component: (await import('../../features/employees/tabs/OverviewTab')).OverviewTab,
                        }),
                      },
                      {
                        path: 'assignments',
                        lazy: async () => {
                          const { AssignmentsTab } = await import('../../features/employees/tabs/AssignmentsTab')
                          return {
                            element: (
                              <RequirePermission permission={PERMISSIONS.EMPLOYEES_HISTORY_VIEW}>
                                <AssignmentsTab />
                              </RequirePermission>
                            ),
                          }
                        },
                      },
                      {
                        path: 'roles',
                        lazy: async () => ({
                          Component: (await import('../../features/employees/tabs/FunctionalRolesTab'))
                            .FunctionalRolesTab,
                        }),
                      },
                      {
                        path: 'responsibilities',
                        lazy: async () => ({
                          Component: (await import('../../features/employees/tabs/ResponsibilitiesTab'))
                            .ResponsibilitiesTab,
                        }),
                      },
                      {
                        path: 'reporting',
                        lazy: async () => ({
                          Component: (await import('../../features/employees/tabs/ReportingTab')).ReportingTab,
                        }),
                      },
                      {
                        path: 'account',
                        lazy: async () => ({
                          Component: (await import('../../features/employees/tabs/AccountTab')).AccountTab,
                        }),
                      },
                      {
                        path: 'history',
                        lazy: async () => {
                          const { HistoryTab } = await import('../../features/employees/tabs/HistoryTab')
                          return {
                            element: (
                              <RequirePermission permission={PERMISSIONS.EMPLOYEES_HISTORY_VIEW}>
                                <HistoryTab />
                              </RequirePermission>
                            ),
                          }
                        },
                      },
                    ],
                  },
                ],
              },
              { path: '*', element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]
