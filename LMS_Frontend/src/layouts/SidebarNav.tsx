import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { NAV_ITEMS } from '../app/navigation'

interface SidebarNavProps {
  onNavigate?: () => void
}

const available = NAV_ITEMS.filter((item) => item.status === 'available' && item.to)
const planned = NAV_ITEMS.filter((item) => item.status === 'planned')

/**
 * Planned modules are grouped under one "Coming soon" heading rather than
 * carrying a badge each: translated labels can be long, and per-item badges
 * would truncate them on narrow sidebars.
 */
export function SidebarNav({ onNavigate }: SidebarNavProps) {
  const { t } = useTranslation()
  const plannedHeadingId = useId()

  return (
    <nav aria-label={t('nav.label')} className="p-3">
      <ul className="space-y-1">
        {available.map(({ id, labelKey, icon: Icon, to }) => (
          <li key={id}>
            <NavLink
              to={to ?? '/'}
              end
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none ${
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              <Icon aria-hidden="true" className="size-5 shrink-0" />
              <span className="min-w-0">{t(labelKey)}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      <p
        id={plannedHeadingId}
        className="mt-6 mb-1 px-3 text-xs font-semibold tracking-wide text-slate-500 uppercase"
      >
        {t('nav.comingSoon')}
      </p>
      <ul aria-labelledby={plannedHeadingId} className="space-y-1">
        {planned.map(({ id, labelKey, icon: Icon }) => (
          <li
            key={id}
            aria-disabled="true"
            className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-400"
          >
            <Icon aria-hidden="true" className="size-5 shrink-0" />
            <span className="min-w-0">{t(labelKey)}</span>
          </li>
        ))}
      </ul>
    </nav>
  )
}
