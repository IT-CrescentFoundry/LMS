import { useTranslation } from 'react-i18next'

import { ApiError } from '../../lib/apiClient'

/**
 * Backend error codes of the training, competency and notification APIs that the UI
 * explains in the user's language. Anything else falls back to a generic message with
 * the request reference.
 */
export const FEATURE_ERROR_CODES = [
  'schema_migration_pending',
  'version_conflict',
  'forbidden',
  'title_required',
  'invalid_code',
  'training_programme_code_taken',
  'training_event_code_taken',
  'training_event_cancelled',
  'training_event_closed',
  'training_event_not_found',
  'invalid_initial_status',
  'status_unchanged',
  'status_transition_not_allowed',
  'reason_required',
  'schedule_dates_required',
  'actual_dates_required',
  'actual_date_in_future',
  'actual_start_required',
  'planned_period_invalid',
  'actual_period_invalid',
  'trainer_type_mismatch',
  'session_period_invalid',
  'session_too_long',
  'invalid_nomination_status',
  'employee_separated',
  'employee_not_found',
  'attendance_not_allowed',
  'event_not_started',
  'minutes_need_attendance',
  'completion_not_allowed',
  'completion_needs_attendance',
  'certificate_needs_completion',
  'withdraw_after_attendance',
  'invalid_range',
  'notification_mandatory',
  'proficiency_scale_code_taken',
  'competency_code_taken',
  'skill_matrix_code_taken',
  'levels_not_unique',
  'level_in_use',
  'competent_rank_invalid',
  'competency_assessed',
  'matrix_has_items',
  'duplicate_competency',
  'scale_mismatch',
  'level_not_in_scale',
  'scale_unknown',
  'assessed_in_future',
  'self_assessment',
  'add_and_remove',
  'employee_not_linked',
  'validation_error',
] as const
export type FeatureErrorCode = (typeof FEATURE_ERROR_CODES)[number]

export function isFeatureErrorCode(value: string | undefined): value is FeatureErrorCode {
  return (FEATURE_ERROR_CODES as readonly (string | undefined)[]).includes(value)
}

/** Translated message for a failed request of the first-release modules. */
export function useFeatureErrorMessage() {
  const { t } = useTranslation()
  return (error: unknown): string => {
    if (error instanceof ApiError) {
      if (error.kind === 'network' || error.kind === 'timeout') return t('auth.errors.network')
      if (isFeatureErrorCode(error.code)) return t(`feature.errors.${error.code}`)
      if (error.code) {
        return error.requestId
          ? t('emp.errors.unknownCodeWithReference', { code: error.code, requestId: error.requestId })
          : t('emp.errors.unknownCode', { code: error.code })
      }
    }
    return t('auth.errors.generic')
  }
}
