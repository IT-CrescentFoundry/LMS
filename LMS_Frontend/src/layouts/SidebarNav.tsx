import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { visibleNavItems, type NavItem } from '../app/navigation'
import { useAuth } from '../features/auth/authContext'

interface SidebarNavProps {
  onNavigate?: () => void
}

function NavLinks({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  const { t } = useTranslation()
  return items.map(({ id, labelKey, icon: Icon, to, matchNested }) => (
    <li key={id}>
      <NavLink
        to={to ?? '/'}
        end={!matchNested}
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
  ))
}

/**
 * Planned modules are grouped under one "Coming soon" heading rather than
 * carrying a badge each: translated labels can be long, and per-item badges
 * would truncate them on narrow sidebars.
 *
 * The Administration group lists only pages the user has permission for.
 * Hiding a link is not a security boundary: the pages and the API check
 * permissions themselves.
 */
export function SidebarNav({ onNavigate }: SidebarNavProps) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const adminHeadingId = useId()
  const plannedHeadingId = useId()

  const items = visibleNavItems(user)
  const main = items.filter((item) => item.group === 'main' && item.status === 'available')
  const admin = items.filter((item) => item.group === 'administration' && item.status === 'available')
  const planned = items.filter((item) => item.status === 'planned')

  return (
    <nav aria-label={t('nav.label')} className="p-3">
      <ul className="space-y-1">
        <NavLinks items={main} onNavigate={onNavigate} />
      </ul>

      {admin.length > 0 ? (
        <>
          <p
            id={adminHeadingId}
            className="mt-6 mb-1 px-3 text-xs font-semibold tracking-wide text-slate-500 uppercase"
          >
            {t('nav.administration')}
          </p>
          <ul aria-labelledby={adminHeadingId} className="space-y-1">
            <NavLinks items={admin} onNavigate={onNavigate} />
          </ul>
        </>
      ) : null}

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
