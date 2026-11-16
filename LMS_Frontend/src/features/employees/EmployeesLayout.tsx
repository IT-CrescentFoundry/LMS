import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'

import { useAuth } from '../auth/authContext'
import { hasPermission } from '../auth/permissions'
import { EMPLOYEE_SECTIONS } from './sections'

/**
 * Shell of the employee directory pages: section pills (Directory, Data quality)
 * in the Organisation Builder style - wrapping, never a hidden horizontal scroll.
 * A section is listed only for users holding its permission; the routes are
 * guarded as well, and the API enforces every permission. Employee profiles have
 * their own header and tabs and are not rendered inside this shell.
 */
export function EmployeesLayout() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const sections = EMPLOYEE_SECTIONS.filter((section) => hasPermission(user, section.permission))

  return (
    <div className="space-y-6">
      {sections.length > 1 ? (
        <nav aria-label={t('emp.nav.label')}>
          <ul className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
            {sections.map((section) => (
              <li key={section.path}>
                <NavLink
                  to={section.path}
                  end
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
      ) : null}
      <Outlet />
    </div>
  )
}
