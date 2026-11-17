import { ApiError } from '../../lib/apiClient'

/**
 * HTTP error codes of the import API (docs/architecture/API_REFERENCE.md section
 * 10) plus shared codes, translated under `imp.errors.codes`. The backend's
 * English message is never shown; an unknown code is shown by name with the
 * request reference.
 */
export const IMPORT_ERROR_CODES = [
  'import_job_not_found',
  'import_profile_not_found',
  'import_row_not_found',
  'import_mapping_not_found',
  'import_invalid_transition',
  'import_profile_unavailable',
  'import_mapping_not_confirmed',
  'import_not_ready',
  'import_preview_expired',
  'import_revalidation_required',
  'import_mapping_already_decided',
  'import_mapping_not_decided',
  'import_file_unavailable',
  'import_job_expired',
  'import_records_changed',
  'import_too_many_rows',
  'import_storage_unavailable',
  'version_conflict',
  'file_too_large',
  'file_type_not_allowed',
  'file_extension_not_allowed',
  'file_empty',
  'file_encrypted_or_legacy',
  'file_not_xlsx',
  'file_corrupted',
  'file_macro_enabled',
  'file_unsafe_entry',
  'file_expansion_limit',
  'file_too_complex',
  'file_too_many_sheets',
  'sheet_too_many_rows',
  'sheet_too_many_columns',
  'import_mapping_empty',
  'import_mapping_unknown_section',
  'import_mapping_unknown_sheet',
  'import_mapping_duplicate_section',
  'import_mapping_header_row',
  'import_mapping_unknown_field',
  'import_mapping_field_twice',
  'import_mapping_unknown_column',
  'import_mapping_column_excluded',
  'import_mapping_required_missing',
  'import_decision_invalid',
  'import_skip_reason_required',
  'import_mapping_target_not_found',
  'import_mapping_target_inactive',
  'validation_error',
  'invalid_cursor',
  'forbidden',
  'password_change_required',
] as const
export type ImportErrorCode = (typeof IMPORT_ERROR_CODES)[number]

/**
 * Row-level issue codes of profile `employees` v1 (translated under `imp.issues`).
 * Domain-rule codes reported by the dry run (e.g. `primary_overlap`) reuse the
 * employee screens' translations; anything else is shown by name.
 */
export const IMPORT_ISSUE_CODES = [
  'required',
  'employee_code_invalid',
  'employee_code_numeric',
  'date_invalid',
  'date_ambiguous',
  'date_numeric',
  'date_has_time',
  'status_invalid',
  'language_invalid',
  'assignment_type_invalid',
  'email_invalid',
  'text_expected',
  'value_too_long',
  'last_day_before_start',
  'last_working_day_requires_separated',
  'separated_requires_last_working_day',
  'row_hidden',
  'row_merged_cells',
  'duplicate_in_file',
  'probable_duplicate',
  'depends_on_invalid_row',
  'reference_unmapped',
  'employee_not_found',
  'manager_not_found',
  'assignment_conflicts_existing',
  'reporting_conflicts_existing',
  'status_change_not_applied',
  'separation_not_applied',
  'unit_type_not_assignable',
] as const
export type ImportIssueCode = (typeof IMPORT_ISSUE_CODES)[number]

export function isImportErrorCode(value: string | undefined): value is ImportErrorCode {
  return (IMPORT_ERROR_CODES as readonly (string | undefined)[]).includes(value)
}

export function isImportIssueCode(value: string): value is ImportIssueCode {
  return (IMPORT_ISSUE_CODES as readonly string[]).includes(value)
}

export type ImportErrorDescription =
  | { kind: 'code'; code: ImportErrorCode; requestId?: string }
  | { kind: 'unknown_code'; code: string; requestId?: string }
  | { kind: 'network' }
  | { kind: 'generic'; requestId?: string }

export function describeImportError(error: unknown): ImportErrorDescription {
  if (!(error instanceof ApiError)) return { kind: 'generic' }
  if (error.kind === 'network' || error.kind === 'timeout') return { kind: 'network' }
  if (isImportErrorCode(error.code)) return { kind: 'code', code: error.code, requestId: error.requestId }
  if (error.code) return { kind: 'unknown_code', code: error.code, requestId: error.requestId }
  return { kind: 'generic', requestId: error.requestId }
}

/** Conflicts that are resolved by reloading the job (someone else acted first). */
export function needsReload(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.code === 'version_conflict' ||
      error.code === 'import_invalid_transition' ||
      error.code === 'import_not_ready' ||
      error.code === 'import_job_expired' ||
      error.code === 'import_mapping_already_decided')
  )
}
