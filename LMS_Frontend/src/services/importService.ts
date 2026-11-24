/**
 * Import Control Room API (Stage D endpoints under `/imports`).
 *
 * Every route needs `imports.view`; uploading, mapping, validating, row decisions
 * and cancelling need `imports.<profile>.run`; the commit needs
 * `imports.<profile>.commit` plus the domain permissions it writes with; mapping
 * decisions need `imports.mappings.manage`. The backend enforces all of them.
 *
 * The workbook is uploaded as the raw request body (never a form) with its display
 * name in `X-File-Name`. Parsers copy known fields only; row values are reduced to
 * plain text, numbers and booleans.
 */

import { apiRequest, buildQuery, isRecord } from '../lib/apiClient'
import {
  expectBoolean,
  expectDateString,
  expectInteger,
  expectNullableDateString,
  expectNullableInteger,
  expectNullableString,
  expectOneOf,
  expectRecord,
  expectString,
  expectStringArray,
} from '../lib/parse'
import type { Page } from '../types/admin'
import {
  IMPORT_STATUSES,
  ISSUE_SEVERITIES,
  MAPPING_STATUSES,
  ROW_DECISIONS,
  type CommittedCounts,
  type Download,
  type ImportCounts,
  type ImportIssue,
  type ImportJob,
  type ImportJobSummary,
  type ImportProfile,
  type ImportRow,
  type IssueFilters,
  type JobFilters,
  type MappingFilters,
  type MappingSection,
  type MappingSuggestion,
  type ProfileField,
  type ProfileSection,
  type RowDecision,
  type RowFilters,
  type SheetHeader,
  type ValueMapping,
  type WorkbookSheet,
} from '../types/imports'
import { parseActor, parsePage } from './adminService'
import { parseRef } from './organisationService'

export const IMPORT_PAGE_SIZE = 25
export const ROW_PAGE_SIZE = 50
export const XLSX_MEDIA_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
/** Validation and commit run every row through the domain rules: allow time. */
export const LONG_REQUEST_TIMEOUT_MS = 300_000

type Plain = string | number | boolean | null

// ------------------------------------------------------------------- parsers

function list<T>(data: unknown, what: string, parseItem: (item: unknown) => T): T[] {
  if (!Array.isArray(data)) throw new TypeError(`${what}: expected a list`)
  return data.map(parseItem)
}

function plainValue(value: unknown): Plain {
  if (value === null || value === undefined) return null
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value
  return null // nested structures are never rendered
}

function plainRecord(data: unknown): Record<string, Plain> {
  if (!isRecord(data)) return {}
  return Object.fromEntries(Object.entries(data).map(([key, value]) => [key, plainValue(value)]))
}

function numberRecord(data: unknown): Record<string, number> {
  if (!isRecord(data)) return {}
  return Object.fromEntries(
    Object.entries(data).filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
  )
}

function stringRecord(data: unknown): Record<string, string> {
  if (!isRecord(data)) return {}
  return Object.fromEntries(
    Object.entries(data).filter((entry): entry is [string, string] => typeof entry[1] === 'string'),
  )
}

function parseField(data: unknown): ProfileField {
  const record = expectRecord(data, 'profile field')
  return {
    name: expectString(record, 'name'),
    type: expectString(record, 'type'),
    required: expectBoolean(record, 'required'),
    aliases: expectStringArray(record, 'aliases'),
    reference: expectNullableString(record, 'reference'),
  }
}

function parseSection(data: unknown): ProfileSection {
  const record = expectRecord(data, 'profile section')
  return {
    kind: expectString(record, 'kind'),
    sheet_aliases: expectStringArray(record, 'sheet_aliases'),
    natural_key: expectStringArray(record, 'natural_key'),
    fields: list(record.fields, 'fields', parseField),
  }
}

export function parseProfile(data: unknown): ImportProfile {
  const record = expectRecord(data, 'import profile')
  return {
    code: expectString(record, 'code'),
    version: expectInteger(record, 'version'),
    commit_mode: expectString(record, 'commit_mode'),
    sections: list(record.sections, 'sections', parseSection),
    can_run: expectBoolean(record, 'can_run'),
    can_commit: expectBoolean(record, 'can_commit'),
  }
}

function parseHeader(data: unknown): SheetHeader {
  const record = expectRecord(data, 'header')
  return {
    column: expectString(record, 'column'),
    index: expectInteger(record, 'index'),
    text: expectString(record, 'text'),
    excluded: expectBoolean(record, 'excluded'),
    suggested_field: expectNullableString(record, 'suggested_field'),
  }
}

function parseSheet(data: unknown): WorkbookSheet {
  const record = expectRecord(data, 'sheet')
  return {
    name: expectString(record, 'name'),
    state: expectString(record, 'state'),
    dimensions: expectNullableString(record, 'dimensions'),
    suggested_section: expectNullableString(record, 'suggested_section'),
    header_row: expectNullableInteger(record, 'header_row'),
    headers: list(record.headers, 'headers', parseHeader),
  }
}

function parseMappingSection(data: unknown): MappingSection {
  const record = expectRecord(data, 'mapping section')
  return {
    section: expectString(record, 'section'),
    sheet: expectString(record, 'sheet'),
    header_row: expectInteger(record, 'header_row'),
    columns: stringRecord(record.columns),
  }
}

function parseCommitted(data: unknown): CommittedCounts | undefined {
  if (!isRecord(data)) return undefined
  const counts = numberRecord(data)
  return {
    created: counts.created ?? 0,
    updated: counts.updated ?? 0,
    unchanged: counts.unchanged ?? 0,
    skipped: counts.skipped ?? 0,
  }
}

function parseCounts(data: unknown): ImportCounts {
  if (!isRecord(data)) return {}
  const numbers = numberRecord(data)
  const bySection = isRecord(data.by_section)
    ? Object.fromEntries(Object.entries(data.by_section).map(([key, value]) => [key, numberRecord(value)]))
    : undefined
  return {
    rows: numbers.rows,
    blocking_errors: numbers.blocking_errors,
    error_rows: numbers.error_rows,
    warnings: numbers.warnings,
    undecided_duplicates: numbers.undecided_duplicates,
    importable: numbers.importable,
    skipped_rows: numbers.skipped_rows,
    skipped_blank: numbers.skipped_blank,
    skipped_repeated_header: numbers.skipped_repeated_header,
    by_section: bySection,
    committed: parseCommitted(data.committed),
  }
}

function summaryFields(record: Record<string, unknown>): ImportJobSummary {
  return {
    public_id: expectString(record, 'public_id'),
    profile_code: expectString(record, 'profile_code'),
    profile_version: expectInteger(record, 'profile_version'),
    status: expectOneOf(record, 'status', IMPORT_STATUSES),
    original_filename: expectString(record, 'original_filename'),
    file_size: expectInteger(record, 'file_size'),
    uploaded_by: parseActor(record.uploaded_by),
    uploaded_at: expectDateString(record, 'uploaded_at'),
    validated_at: expectNullableDateString(record, 'validated_at'),
    committed_at: expectNullableDateString(record, 'committed_at'),
    finished_at: expectNullableDateString(record, 'finished_at'),
    counts: parseCounts(record.counts),
  }
}

export function parseJobSummary(data: unknown): ImportJobSummary {
  return summaryFields(expectRecord(data, 'import job'))
}

export function parseJob(data: unknown): ImportJob {
  const record = expectRecord(data, 'import job')
  return {
    ...summaryFields(record),
    file_sha256: expectString(record, 'file_sha256'),
    file_stored: expectBoolean(record, 'file_stored'),
    workbook: list(record.workbook, 'workbook', parseSheet),
    column_mapping: list(record.column_mapping, 'column_mapping', parseMappingSection),
    mapping_confirmed: expectBoolean(record, 'mapping_confirmed'),
    previously_imported_by: expectStringArray(record, 'previously_imported_by'),
    failure_code: expectNullableString(record, 'failure_code'),
    validated_by: parseActor(record.validated_by),
    committed_by: parseActor(record.committed_by),
    version: expectInteger(record, 'version'),
  }
}

export function parseIssue(data: unknown): ImportIssue {
  const record = expectRecord(data, 'issue')
  return {
    id: expectInteger(record, 'id'),
    section: expectNullableString(record, 'section'),
    sheet: expectNullableString(record, 'sheet'),
    row_number: expectNullableInteger(record, 'row_number'),
    column: expectNullableString(record, 'column'),
    field: expectNullableString(record, 'field'),
    code: expectString(record, 'code'),
    severity: expectOneOf(record, 'severity', ISSUE_SEVERITIES),
    source_value: expectNullableString(record, 'source_value'),
    params: isRecord(record.params) ? record.params : null,
  }
}

function parseChanges(data: unknown): ImportRow['changes'] {
  if (!isRecord(data)) return null
  const changes: NonNullable<ImportRow['changes']> = {}
  for (const [field, change] of Object.entries(data)) {
    if (isRecord(change)) {
      changes[field] = { from: plainValue(change.from), to: plainValue(change.to) }
      if (typeof change.effective_date === 'string') changes[field].effective_date = change.effective_date
    }
  }
  return changes
}

export function parseRow(data: unknown): ImportRow {
  const record = expectRecord(data, 'row')
  const decision = record.decision
  return {
    id: expectInteger(record, 'id'),
    section: expectString(record, 'section'),
    sheet: expectString(record, 'sheet'),
    row_number: expectInteger(record, 'row_number'),
    outcome: expectString(record, 'outcome'),
    values: plainRecord(record.values),
    source: plainRecord(record.source),
    changes: parseChanges(record.changes),
    decision:
      decision === null || decision === undefined ? null : (expectOneOf(record, 'decision', ROW_DECISIONS) as RowDecision),
    decision_reason: expectNullableString(record, 'decision_reason'),
    target_public_id: expectNullableString(record, 'target_public_id'),
    issues: list(record.issues, 'issues', parseIssue),
  }
}

function parseSuggestion(data: unknown): MappingSuggestion {
  const record = expectRecord(data, 'suggestion')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    label: expectString(record, 'label'),
    score: expectInteger(record, 'score'),
    reason: expectString(record, 'reason'),
  }
}

export function parseValueMapping(data: unknown): ValueMapping {
  const record = expectRecord(data, 'value mapping')
  return {
    public_id: expectString(record, 'public_id'),
    kind: expectString(record, 'kind'),
    source_text: expectString(record, 'source_text'),
    normalised_text: expectString(record, 'normalised_text'),
    status: expectOneOf(record, 'status', MAPPING_STATUSES),
    target: record.target === null || record.target === undefined ? null : parseRef(record.target),
    decision_reason: expectNullableString(record, 'decision_reason'),
    decided_by: parseActor(record.decided_by),
    decided_at: expectNullableDateString(record, 'decided_at'),
    created_at: expectDateString(record, 'created_at'),
    suggestions: list(record.suggestions, 'suggestions', parseSuggestion),
    version: expectInteger(record, 'version'),
  }
}

function parseBlob(data: unknown): Blob {
  if (!(data instanceof Blob)) throw new TypeError('download: expected a file')
  return data
}

// --------------------------------------------------------------------- calls

const json = <T>(parse: (data: unknown) => T) => ({ parse })

export const importService = {
  listProfiles(signal?: AbortSignal): Promise<ImportProfile[]> {
    return apiRequest('/imports/profiles', {
      ...json((data) => list(data, 'profiles', parseProfile)),
      signal,
    })
  },

  async downloadTemplate(profile: ImportProfile): Promise<Download> {
    const blob = await apiRequest(`/imports/profiles/${encodeURIComponent(profile.code)}/template`, {
      parse: parseBlob,
      responseType: 'blob',
    })
    return { blob, filename: `lms-import-${profile.code}-v${profile.version}-template.xlsx` }
  },

  /** Uploads the workbook as the raw body; nothing is parsed or stored in the browser. */
  upload(profile: string, file: File): Promise<ImportJob> {
    return apiRequest(`/imports${buildQuery({ profile })}`, {
      parse: parseJob,
      method: 'POST',
      rawBody: { data: file, contentType: XLSX_MEDIA_TYPE },
      headers: { 'X-File-Name': encodeURIComponent(file.name) },
      timeoutMs: LONG_REQUEST_TIMEOUT_MS,
    })
  },

  listJobs(filters: JobFilters, cursor: string | null, signal?: AbortSignal): Promise<Page<ImportJobSummary>> {
    const query = buildQuery({ ...filters, limit: IMPORT_PAGE_SIZE, cursor })
    return apiRequest(`/imports${query}`, { parse: parsePage(parseJobSummary), signal })
  },

  getJob(id: string, signal?: AbortSignal): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}`, { parse: parseJob, signal })
  },

  setMapping(id: string, body: { version: number; sections: MappingSection[] }): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}/mapping`, { parse: parseJob, method: 'PUT', body })
  },

  validate(id: string, version: number): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}/validate`, {
      parse: parseJob,
      method: 'POST',
      body: { version },
      timeoutMs: LONG_REQUEST_TIMEOUT_MS,
    })
  },

  decideRow(
    id: string,
    rowId: number,
    body: { version: number; decision: RowDecision | null; reason?: string | null },
  ): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}/rows/${rowId}/decision`, {
      parse: parseJob,
      method: 'POST',
      body,
    })
  },

  /** The explicit approval: `confirm` is always true here; the UI asks first. */
  commit(id: string, body: { version: number; apply_updates: boolean }): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}/commit`, {
      parse: parseJob,
      method: 'POST',
      body: { ...body, confirm: true },
      timeoutMs: LONG_REQUEST_TIMEOUT_MS,
    })
  },

  cancel(id: string, version: number): Promise<ImportJob> {
    return apiRequest(`/imports/${encodeURIComponent(id)}/cancel`, {
      parse: parseJob,
      method: 'POST',
      body: { version },
    })
  },

  listRows(id: string, filters: RowFilters, cursor: string | null, signal?: AbortSignal): Promise<Page<ImportRow>> {
    const query = buildQuery({ ...filters, limit: ROW_PAGE_SIZE, cursor })
    return apiRequest(`/imports/${encodeURIComponent(id)}/rows${query}`, { parse: parsePage(parseRow), signal })
  },

  listIssues(
    id: string,
    filters: IssueFilters,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<Page<ImportIssue>> {
    const query = buildQuery({ ...filters, limit: ROW_PAGE_SIZE, cursor })
    return apiRequest(`/imports/${encodeURIComponent(id)}/issues${query}`, { parse: parsePage(parseIssue), signal })
  },

  async downloadErrorReport(id: string): Promise<Download> {
    const blob = await apiRequest(`/imports/${encodeURIComponent(id)}/error-report`, {
      parse: parseBlob,
      responseType: 'blob',
    })
    return { blob, filename: `lms-import-${id}-issues.xlsx` }
  },

  listMappings(
    filters: MappingFilters,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<Page<ValueMapping>> {
    const query = buildQuery({ ...filters, limit: IMPORT_PAGE_SIZE, cursor })
    return apiRequest(`/imports/mappings${query}`, { parse: parsePage(parseValueMapping), signal })
  },

  approveMapping(
    id: string,
    body: { version: number; target_public_id: string; reason?: string | null },
  ): Promise<ValueMapping> {
    return apiRequest(`/imports/mappings/${encodeURIComponent(id)}/approve`, {
      parse: parseValueMapping,
      method: 'POST',
      body,
    })
  },

  rejectMapping(id: string, body: { version: number; reason?: string | null }): Promise<ValueMapping> {
    return apiRequest(`/imports/mappings/${encodeURIComponent(id)}/reject`, {
      parse: parseValueMapping,
      method: 'POST',
      body,
    })
  },

  withdrawMapping(id: string, body: { version: number; reason?: string | null }): Promise<ValueMapping> {
    return apiRequest(`/imports/mappings/${encodeURIComponent(id)}/withdraw`, {
      parse: parseValueMapping,
      method: 'POST',
      body,
    })
  },
}

/** Saves a downloaded file through a temporary object URL (revoked immediately after). */
export function saveDownload({ blob, filename }: Download): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
