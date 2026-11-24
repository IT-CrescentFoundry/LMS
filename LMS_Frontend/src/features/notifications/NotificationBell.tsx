import { Bell } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useNotifications } from '../training/trainingQueries'

/**
 * Header bell with the unread count (polled every minute). Hidden while the
 * notification API is unavailable (not signed in, migration pending, any error).
 */
export function NotificationBell() {
  const { t } = useTranslation()
  const list = useNotifications(false, { poll: true })
  if (!list.data) return null
  const unread = list.data.unread_count
  return (
    <Link
      to="/notifications"
      aria-label={t('notif.bell', { count: unread })}
      className="relative rounded-md p-2 text-white hover:bg-white/10 focus:ring-2 focus:ring-ember-400 focus:outline-none"
    >
      <Bell aria-hidden="true" className="size-5" />
      {unread > 0 ? (
        <span aria-hidden="true" className="absolute -top-0.5 -right-0.5 min-w-5 rounded-full bg-gold-400 px-1 text-center text-xs font-bold text-brand-900">
          {unread > 99 ? '99+' : unread}
        </span>
      ) : null}
    </Link>
  )
}
