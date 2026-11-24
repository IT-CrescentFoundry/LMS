import { Bell, CheckCheck, Lock, PlugZap } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { cardClassName, EmptyState, FeatureError, PageHeader } from '../../components/FeatureState'
import { isHiddenError, isSchemaPending } from '../../lib/featureErrors'
import { secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDateTime } from '../../lib/format'
import { notificationService } from '../../services/notificationService'
import type { AppNotification } from '../../types/training'
import { useFeatureErrorMessage } from '../training/trainingErrors'
import {
  useChannels,
  useNotificationMutation,
  useNotificationPreferences,
  useNotifications,
} from '../training/trainingQueries'
import { useNotificationTypeLabel } from './notificationLabels'


/** Only in-portal paths are followed (the server sends paths, never external URLs). */
function safePath(path: string | null): string | null {
  return path && path.startsWith('/') && !path.startsWith('//') ? path : null
}

/** Notification centre: messages, preferences and delivery channels. */
export function NotificationsPage() {
  const { t } = useTranslation()
  const [unreadOnly, setUnreadOnly] = useState(false)
  const list = useNotifications(unreadOnly)
  const markAll = useNotificationMutation(() => notificationService.markAllRead())
  const message = useFeatureErrorMessage()
  const unreadId = useId()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('notif.title')}
        description={t('notif.description')}
        actions={
          list.data && list.data.unread_count > 0 ? (
            <button type="button" onClick={() => markAll.mutate(undefined)} disabled={markAll.isPending} className={secondaryButtonClassName}>
              <CheckCheck aria-hidden="true" className="size-4" />
              {t('notif.markAll')}
            </button>
          ) : null
        }
      />
      {markAll.error ? <p role="alert" className="text-sm text-red-800">{message(markAll.error)}</p> : null}
      <label htmlFor={unreadId} className="flex items-center gap-2 text-sm">
        <input id={unreadId} type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} className="size-4 accent-brand-700" />
        {t('notif.unreadOnly')}
      </label>
      {list.isPending ? (
        <LoadingState />
      ) : list.isError ? (
        <FeatureError error={list.error} title={t('notif.loadError')} onRetry={() => void list.refetch()} />
      ) : list.data.items.length === 0 ? (
        <EmptyState title={unreadOnly ? t('notif.emptyUnread') : t('notif.empty')} />
      ) : (
        <ul className="space-y-2" aria-label={t('notif.listLabel')}>
          {list.data.items.map((item) => (
            <NotificationRow key={item.public_id} item={item} />
          ))}
        </ul>
      )}
      {list.isError && isSchemaPending(list.error) ? null : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Preferences />
          <Channels />
        </div>
      )}
    </div>
  )
}

function NotificationRow({ item }: { item: AppNotification }) {
  const { t, i18n } = useTranslation()
  const typeLabel = useNotificationTypeLabel()
  const toggle = useNotificationMutation((read: boolean) => notificationService.markRead(item.public_id, read))
  const path = safePath(item.link_path)
  const unread = item.read_at === null
  return (
    <li className={`${cardClassName} flex flex-wrap items-start justify-between gap-3 ${unread ? 'border-l-4 border-l-gold-400' : ''}`}>
      <div className="min-w-0 space-y-1">
        <p className="text-xs text-slate-500">
          {typeLabel(item.notification_type)} · {formatDateTime(item.created_at, i18n.resolvedLanguage)}
          {unread ? <span className="ml-2 font-semibold text-slate-800">{t('notif.unread')}</span> : null}
        </p>
        <p className={`break-words ${unread ? 'font-semibold text-slate-900' : 'text-slate-800'}`}>{item.title}</p>
        <p className="text-sm break-words text-slate-600">{item.body}</p>
        {path ? (
          <Link
            to={path}
            onClick={() => {
              if (unread) toggle.mutate(true)
            }}
            className="text-sm font-medium text-brand-700 hover:underline"
          >
            {t('notif.open')}
          </Link>
        ) : null}
      </div>
      <button type="button" onClick={() => toggle.mutate(unread)} disabled={toggle.isPending} className={secondaryButtonClassName}>
        {unread ? t('notif.markRead') : t('notif.markUnread')}
      </button>
    </li>
  )
}

function Preferences() {
  const { t } = useTranslation()
  const prefs = useNotificationPreferences()
  const typeLabel = useNotificationTypeLabel()
  const save = useNotificationMutation(({ type, enabled }: { type: string; enabled: boolean }) =>
    notificationService.setPreference(type, enabled),
  )
  const message = useFeatureErrorMessage()
  if (prefs.isError && isHiddenError(prefs.error)) return null
  return (
    <section aria-labelledby="notif-prefs" className={`${cardClassName} space-y-3`}>
      <h2 id="notif-prefs" className="font-semibold text-slate-900">{t('notif.preferences.title')}</h2>
      <p className="text-sm text-slate-600">{t('notif.preferences.help')}</p>
      {save.error ? <p role="alert" className="text-sm text-red-800">{message(save.error)}</p> : null}
      {prefs.isPending ? (
        <LoadingState />
      ) : prefs.isError ? (
        <FeatureError error={prefs.error} title={t('notif.preferences.loadError')} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {Object.entries(prefs.data.preferences).map(([type, enabled]) => {
            const mandatory = prefs.data.mandatory.includes(type)
            return (
              <li key={type} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span className="flex items-center gap-1.5">
                  {mandatory ? <Lock aria-hidden="true" className="size-3.5 text-slate-500" /> : null}
                  {typeLabel(type)}
                  {mandatory ? <span className="text-xs text-slate-500">({t('notif.preferences.mandatory')})</span> : null}
                </span>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={enabled}
                    disabled={mandatory || save.isPending}
                    onChange={(e) => save.mutate({ type, enabled: e.target.checked })}
                    className="size-4 accent-brand-700"
                    aria-label={t('notif.preferences.toggle', { type: typeLabel(type) })}
                  />
                  {enabled ? t('notif.preferences.on') : t('notif.preferences.off')}
                </label>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function Channels() {
  const { t, i18n } = useTranslation()
  const channels = useChannels()
  if (channels.isError && isHiddenError(channels.error)) return null
  return (
    <section aria-labelledby="notif-channels" className={`${cardClassName} space-y-3`}>
      <h2 id="notif-channels" className="font-semibold text-slate-900">{t('notif.channels.title')}</h2>
      {channels.isPending ? (
        <LoadingState />
      ) : channels.isError ? (
        <FeatureError error={channels.error} title={t('notif.channels.loadError')} />
      ) : (
        <>
          <ul className="space-y-2">
            {channels.data.channels.map((channel) => (
              <li key={channel.code} className="flex items-start justify-between gap-3 text-sm">
                <span className="flex items-center gap-2">
                  {channel.connected ? (
                    <Bell aria-hidden="true" className="size-4 text-emerald-600" />
                  ) : (
                    <PlugZap aria-hidden="true" className="size-4 text-slate-400" />
                  )}
                  {channel.code === 'in_app' || channel.code === 'outlook' || channel.code === 'teams'
                    ? t(`notif.channels.${channel.code}`)
                    : channel.name}
                </span>
                <span className={channel.connected ? 'font-medium text-emerald-800' : 'text-slate-600'}>
                  {channel.connected ? t('notif.channels.connected') : t('notif.channels.notConnected')}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">
            {t('notif.channels.reminders', {
              days: channels.data.reminder_offsets_days
                .map((d) => new Intl.NumberFormat(i18n.resolvedLanguage).format(d))
                .join(', '),
            })}
          </p>
        </>
      )}
    </section>
  )
}
