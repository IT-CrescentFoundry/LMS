import { ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet, useLocation } from 'react-router'

import { ORG_SECTIONS, sectionForPath } from './sections'

/**
 * Shell of the organisation area: breadcrumbs and a section navigation (a
 * horizontally scrollable list on phones). Every section needs
 * `organisation.view`; management controls are gated per page.
 */
export function OrganisationLayout() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const current = sectionForPath(pathname)

  return (
    <div className="space-y-6">
      <nav aria-label={t('org.breadcrumb')}>
        <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-600">
          <li>
            <Link to="/organisation" className="rounded hover:text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none">
              {t('nav.organisation')}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-4 text-slate-400" />
          </li>
          <li aria-current="page" className="font-medium text-slate-900">
            {t(current.labelKey)}
          </li>
        </ol>
      </nav>

      {/* Wrapping links: every section stays visible at every width (no hidden scroll). */}
      <nav aria-label={t('org.nav.label')}>
        <ul className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
          {ORG_SECTIONS.map((section) => (
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

      <Outlet />
    </div>
  )
}
