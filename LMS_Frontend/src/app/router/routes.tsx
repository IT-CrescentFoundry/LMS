import type { RouteObject } from 'react-router'

import { DashboardPage } from '../../features/dashboard/DashboardPage'
import { NotFoundPage } from '../../features/errors/NotFoundPage'
import { RouteErrorPage } from '../../features/errors/RouteErrorPage'
import { AppLayout } from '../../layouts/AppLayout'

/** Route table. Shared by the browser router and by tests (memory router). */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
