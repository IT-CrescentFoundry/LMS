import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'

import { useAuth } from '../auth/authContext'
import { hasAnyPermission, IMPORT_RUN_PERMISSIONS } from '../auth/permissions'

/**
 * Shell of the Import Control Room: section pills (Overview, New import,
 * Reference mappings). "New import" is listed only for users who may run an
 * import profile; the API enforces every permission. A job page is rendered in
 * the same shell so the way back is always visible.
 */
export function ImportsLayout() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const sections = [
    { path: '/imports', labelKey: 'imp.nav.overview', show: true, end: true },
    {
      path: '/imports/new',
      labelKey: 'imp.nav.newImport',
      show: hasAnyPermission(user, IMPORT_RUN_PERMISSIONS),
      end: true,
    },
    { path: '/imports/mappings', labelKey: 'imp.nav.mappings', show: true, end: true },
  ] as const

  return (
    <div className="space-y-6">
      <nav aria-label={t('imp.nav.label')}>
        <ul className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
          {sections
            .filter((section) => section.show)
            .map((section) => (
              <li key={section.path}>
                <NavLink
                  to={section.path}
                  end={section.end}
                  className={({ isActive }) =>
                    `inline-block rounded-full px-3 py-1.5 text-sm font-medium focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 focus:outline-none ${
                      isActive
                        ? 'bg-brand-700 text-white shadow-sm'
                        : 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 hover:text-slate-900'
                    }`
                  }
                >
                  {t(section.labelKey)}
                </NavLink>
              </li>
            ))}
        </ul>
      </nav>
      <Outlet />
    </div>
  )
}
