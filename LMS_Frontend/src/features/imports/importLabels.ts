import { useTranslation } from 'react-i18next'

import type { ImportIssue, ImportStatus } from '../../types/imports'
import { isEmployeeErrorCode } from '../employees/employeeErrors'
import { isOrgErrorCode, isWarningCode } from '../organisation/orgErrors'
import { describeImportError, isImportIssueCode } from './importErrors'

/** Section names of the profile (unknown sections are shown by name). */
export function useSectionLabel() {
  const { t } = useTranslation()
  return (section: string): string =>
    section === 'employees' || section === 'assignments' || section === 'reporting' || section === 'units'
      ? t(`imp.sections.${section}`)
      : section
}

/** Profile field names (unknown fields are shown by name). */
export function useFieldLabel() {
  const { t, i18n } = useTranslation()
  return (field: string): string => {
    const key = `imp.fields.${field}`
    return i18n.exists(`common:${key}`) ? t(key as 'imp.fields.employee_code') : field
  }
}

/** "field: from → to; ..." for `existing_unit_differs` (values are shown as sent). */
function describeDifferences(value: unknown): string {
  if (value === null || typeof value !== 'object') return ''
  return Object.entries(value as Record<string, unknown>)
    .map(([field, change]) => {
      const pair = (change ?? {}) as { from?: unknown; to?: unknown }
      const show = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v))
      return `${field}: ${show(pair.from)} → ${show(pair.to)}`
    })
    .join('; ')
}

/** The translated explanation of one row-level issue. */
export function useIssueMessage() {
  const { t } = useTranslation()
  return (issue: Pick<ImportIssue, 'code' | 'params'>): string => {
    const params = issue.params ?? {}
    if (isImportIssueCode(issue.code)) {
      return t(`imp.issues.${issue.code}`, {
        codes: Array.isArray(params.other_codes) ? params.other_codes.join(', ') : '',
        rows: Array.isArray(params.rows) ? params.rows.join(', ') : '',
        current: typeof params.current === 'string' ? t(`emp.status.${params.current}` as 'emp.status.active') : '',
        max: typeof params.max === 'number' ? params.max : '',
        differences: describeDifferences(params.differences),
      })
    }
    if (isEmployeeErrorCode(issue.code)) return t(`emp.errors.codes.${issue.code}`)
    if (isOrgErrorCode(issue.code)) return t(`org.errors.codes.${issue.code}`)
    if (isWarningCode(issue.code)) return t(`org.warnings.${issue.code}`)
    return t('imp.issues.unknown', { code: issue.code })
  }
}

/** Translated explanation of a failed import request (codes are never hidden). */
export function useImportErrorMessage() {
  const { t } = useTranslation()
  return (error: unknown): string => {
    const described = describeImportError(error)
    switch (described.kind) {
      case 'code':
        return t(`imp.errors.codes.${described.code}`)
      case 'unknown_code':
        return described.requestId
          ? t('emp.errors.unknownCodeWithReference', { code: described.code, requestId: described.requestId })
          : t('emp.errors.unknownCode', { code: described.code })
      case 'network':
        return t('auth.errors.network')
      default:
        return described.requestId
          ? `${t('auth.errors.generic')} ${t('auth.errors.reference', { requestId: described.requestId })}`
          : t('auth.errors.generic')
    }
  }
}

export const IMPORT_STEPS = ['upload', 'map', 'validate', 'approve', 'done'] as const
export type ImportStep = (typeof IMPORT_STEPS)[number]

export function currentStep(status: ImportStatus, mappingConfirmed: boolean): ImportStep {
  switch (status) {
    case 'uploaded':
    case 'mapping_required':
      return mappingConfirmed ? 'validate' : 'map'
    case 'validating':
    case 'validation_failed':
      return 'validate'
    case 'ready_for_approval':
    case 'committing':
      return 'approve'
    default:
      return 'done'
  }
}

export function currentStepIndex(step: ImportStep): number {
  return IMPORT_STEPS.indexOf(step)
}

export function formatBytes(bytes: number, language: string | undefined): string {
  const format = (value: number) => new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(value)
  if (bytes < 1024) return `${format(bytes)} B`
  if (bytes < 1024 * 1024) return `${format(bytes / 1024)} KB`
  return `${format(bytes / (1024 * 1024))} MB`
}

export function formatCount(value: number | undefined, language: string | undefined): string {
  return value === undefined ? '—' : new Intl.NumberFormat(language).format(value)
}
