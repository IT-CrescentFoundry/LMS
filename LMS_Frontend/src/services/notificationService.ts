/**
 * The signed-in user's notification centre (`/notifications`, migration 0011).
 * Opening the list also lets the server create any due training reminders.
 * External channels (Outlook, Teams) are reported as not connected by the server.
 */

import { apiRequest, buildQuery } from '../lib/apiClient'
import {
  expectArray,
  expectBoolean,
  expectDateString,
  expectInteger,
  expectNullableDateString,
  expectNullableString,
  expectRecord,
  expectString,
  expectStringArray,
} from '../lib/parse'
import type {
  AppNotification,
  Channels,
  NotificationList,
  NotificationPreferences,
} from '../types/training'

const NT = '/notifications'

export function parseNotification(data: unknown): AppNotification {
  const r = expectRecord(data, 'notification')
  return {
    public_id: expectString(r, 'public_id'),
    notification_type: expectString(r, 'notification_type'),
    title: expectString(r, 'title'),
    body: expectString(r, 'body'),
    link_path: expectNullableString(r, 'link_path'),
    created_at: expectDateString(r, 'created_at'),
    read_at: expectNullableDateString(r, 'read_at'),
  }
}

export function parseNotificationList(data: unknown): NotificationList {
  const r = expectRecord(data, 'notifications')
  return {
    items: expectArray(r, 'items').map(parseNotification),
    unread_count: expectInteger(r, 'unread_count'),
  }
}

export function parsePreferences(data: unknown): NotificationPreferences {
  const r = expectRecord(data, 'preferences')
  const prefs = expectRecord(r.preferences, 'preferences')
  const parsed: Record<string, boolean> = {}
  for (const key of Object.keys(prefs)) parsed[key] = expectBoolean(prefs, key)
  return { preferences: parsed, mandatory: expectStringArray(r, 'mandatory') }
}

export function parseChannels(data: unknown): Channels {
  const r = expectRecord(data, 'channels')
  const offsets = expectArray(r, 'reminder_offsets_days')
  if (!offsets.every((value) => typeof value === 'number')) {
    throw new TypeError('reminder_offsets_days: expected numbers')
  }
  return {
    channels: expectArray(r, 'channels').map((item) => {
      const c = expectRecord(item, 'channel')
      return {
        code: expectString(c, 'code'),
        name: expectString(c, 'name'),
        connected: expectBoolean(c, 'connected'),
        detail: expectString(c, 'detail'),
      }
    }),
    reminder_offsets_days: offsets as number[],
  }
}

export const notificationService = {
  list(options: { unreadOnly?: boolean; limit?: number }, signal?: AbortSignal): Promise<NotificationList> {
    const query = buildQuery({ unread_only: options.unreadOnly ? true : undefined, limit: options.limit })
    return apiRequest(`${NT}${query}`, { parse: parseNotificationList, signal })
  },
  markRead(id: string, read: boolean): Promise<AppNotification> {
    return apiRequest(`${NT}/${encodeURIComponent(id)}/read`, {
      method: 'POST',
      body: { read },
      parse: parseNotification,
    })
  },
  markAllRead(): Promise<number> {
    return apiRequest(`${NT}/read-all`, {
      method: 'POST',
      parse: (data) => expectInteger(expectRecord(data, 'result'), 'marked'),
    })
  },
  preferences(signal?: AbortSignal): Promise<NotificationPreferences> {
    return apiRequest(`${NT}/preferences`, { parse: parsePreferences, signal })
  },
  setPreference(notificationType: string, enabled: boolean): Promise<NotificationPreferences> {
    return apiRequest(`${NT}/preferences`, {
      method: 'PUT',
      body: { notification_type: notificationType, in_app_enabled: enabled },
      parse: parsePreferences,
    })
  },
  channels(signal?: AbortSignal): Promise<Channels> {
    return apiRequest(`${NT}/channels`, { parse: parseChannels, signal })
  },
}
