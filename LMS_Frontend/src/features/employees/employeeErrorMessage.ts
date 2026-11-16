import { useTranslation } from 'react-i18next'

import { serverFieldIssues, type EmployeeErrorDescription } from './employeeErrors'

/** Translated explanation of an employee API failure (codes are never hidden). */
export function useEmployeeErrorMessage() {
  const { t } = useTranslation()
  return (described: EmployeeErrorDescription): string => {
    switch (described.kind) {
      case 'code':
        return t(`emp.errors.codes.${described.code}`)
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

/**
 * Field messages for a server `validation_error`, by request field name (e.g.
 * `employee_code`). Client-side checks run first; this covers what only the
 * server can judge. The form-level error stays visible as well.
 */
export function useServerFieldErrors(error: unknown): (field: string) => string | undefined {
  const { t } = useTranslation()
  const issues = serverFieldIssues(error)
  return (field) => {
    const kind = issues.get(field)
    return kind ? t(`emp.validation.server.${kind}`) : undefined
  }
}
