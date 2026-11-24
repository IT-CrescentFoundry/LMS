import { useTranslation } from 'react-i18next'

const KNOWN_TYPES = [
  'training.nominated',
  'training.schedule_published',
  'training.schedule_changed',
  'training.cancelled',
  'training.reminder',
  'training.completed',
  'training.certificate_recorded',
] as const
type KnownType = (typeof KNOWN_TYPES)[number]

function typeKey(type: string): string | null {
  return (KNOWN_TYPES as readonly string[]).includes(type) ? (type as KnownType).replace('training.', '') : null
}

export function useNotificationTypeLabel() {
  const { t } = useTranslation()
  return (type: string): string => {
    const key = typeKey(type)
    return key ? t(`notif.types.${key as 'reminder'}`) : type
  }
}
