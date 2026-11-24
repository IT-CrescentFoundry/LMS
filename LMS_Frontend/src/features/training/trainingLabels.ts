import { useTranslation } from 'react-i18next'

import { formatDate } from '../../lib/format'
import { DELIVERY_MODES, NOMINATION_STATUSES } from '../../types/training'

export function isDeliveryMode(value: string | null): value is (typeof DELIVERY_MODES)[number] {
  return value !== null && (DELIVERY_MODES as readonly string[]).includes(value)
}

export function useDeliveryModeLabel() {
  const { t } = useTranslation()
  return (mode: string | null): string => (isDeliveryMode(mode) ? t(`training.mode.${mode}`) : (mode ?? '—'))
}

/** "1 Mar 2027", "1 – 3 Mar 2027" or "Mar 2027 (date not fixed)". */
export function useWhenText() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  return (input: {
    start: string | null
    end: string | null
    planned_month?: string | null
    planned_start_date?: string | null
    actual_start_date?: string | null
  }): string => {
    const monthOnly =
      input.planned_month && !input.planned_start_date && !input.actual_start_date ? input.planned_month : null
    if (monthOnly) {
      const [year, month] = monthOnly.split('-').map(Number)
      const label = new Intl.DateTimeFormat(language, { month: 'long', year: 'numeric' }).format(
        new Date(year, month - 1, 1),
      )
      return t('training.monthOnly', { month: label })
    }
    if (!input.start) return t('training.noDate')
    if (!input.end || input.end === input.start) return formatDate(input.start, language)
    return `${formatDate(input.start, language)} – ${formatDate(input.end, language)}`
  }
}

/** Minutes as "1 h 30 min". */
export function useDurationText() {
  const { t } = useTranslation()
  return (minutes: number | null): string => {
    if (minutes === null) return '—'
    const hours = Math.floor(minutes / 60)
    const rest = minutes % 60
    if (hours === 0) return t('training.durationMinutes', { minutes: rest })
    if (rest === 0) return t('training.durationHours', { hours })
    return t('training.durationHoursMinutes', { hours, minutes: rest })
  }
}

export function useNominationText() {
  const { t } = useTranslation()
  return (value: string): string =>
    (NOMINATION_STATUSES as readonly string[]).includes(value)
      ? t(`training.nomination.${value as (typeof NOMINATION_STATUSES)[number]}`)
      : value
}
