/**
 * Mirrors the Stage D import schemas in LMS_Backend/app/schemas/imports.py
 * (docs/architecture/API_REFERENCE.md section 10). Workbook cell values reach the
 * browser only in a job's staged rows and issues - for mapped columns only.
 */

import type { AuditActor } from './admin'
import type { Ref } from './organisation'

export const IMPORT_STATUSES = [
  'uploaded',
  'mapping_required',
  'validating',
  'validation_failed',
  'ready_for_approval',
  'committing',
  'completed',
  'completed_with_skips',
  'failed',
  'expired',
  'cancelled',
] as const
export type ImportStatus = (typeof IMPORT_STATUSES)[number]

/** Closed jobs: read-only, the stored file is deleted. */
export const TERMINAL_IMPORT_STATUSES: readonly ImportStatus[] = [
  'completed',
  'completed_with_skips',
  'failed',
  'expired',
  'cancelled',
]

export const ROW_OUTCOMES = ['new', 'update', 'unchanged', 'error', 'skipped'] as const
export type RowOutcome = (typeof ROW_OUTCOMES)[number]

export const ROW_DECISIONS = ['skip', 'distinct'] as const
export type RowDecision = (typeof ROW_DECISIONS)[number]

export const ISSUE_SEVERITIES = ['error', 'warning'] as const
export type IssueSeverity = (typeof ISSUE_SEVERITIES)[number]

export const MAPPING_KINDS = ['org_unit', 'designation', 'location', 'grade', 'job_level'] as const
export type MappingKind = (typeof MAPPING_KINDS)[number]

export const MAPPING_STATUSES = ['pending', 'approved', 'rejected', 'superseded'] as const
export type MappingStatus = (typeof MAPPING_STATUSES)[number]

/** Sections of profile `employees` v1 (translated under `imp.sections`). */
export const KNOWN_SECTIONS = ['employees', 'assignments', 'reporting'] as const

export function isImportStatus(value: string | null | undefined): value is ImportStatus {
  return (IMPORT_STATUSES as readonly (string | null | undefined)[]).includes(value)
}

export function isTerminal(status: ImportStatus): boolean {
  return TERMINAL_IMPORT_STATUSES.includes(status)
}

export function isMappingKind(value: string | null | undefined): value is MappingKind {
  return (MAPPING_KINDS as readonly (string | null | undefined)[]).includes(value)
}

export function isMappingStatus(value: string | null | undefined): value is MappingStatus {
  return (MAPPING_STATUSES as readonly (string | null | undefined)[]).includes(value)
}

export function isRowOutcome(value: string | null | undefined): value is RowOutcome {
  return (ROW_OUTCOMES as readonly (string | null | undefined)[]).includes(value)
}

export interface ProfileField {
  name: string
  type: string
  required: boolean
  aliases: string[]
  reference: string | null
}

export interface ProfileSection {
  kind: string
  sheet_aliases: string[]
  natural_key: string[]
  fields: ProfileField[]
}

export interface ImportProfile {
  code: string
  version: number
  commit_mode: string
  sections: ProfileSection[]
  can_run: boolean
  can_commit: boolean
}

export interface SheetHeader {
  /** Column letter, e.g. "C". */
  column: string
  /** 1-based column index. */
  index: number
  text: string
  /** Sensitive or irrelevant data: never mappable, cells never read. */
  excluded: boolean
  suggested_field: string | null
}

export interface WorkbookSheet {
  name: string
  state: string
  dimensions: string | null
  suggested_section: string | null
  header_row: number | null
  headers: SheetHeader[]
}

export interface MappingSection {
  section: string
  sheet: string
  header_row: number
  /** 1-based column index (as a string) -> profile field. */
  columns: Record<string, string>
}

export interface CommittedCounts {
  created: number
  updated: number
  unchanged: number
  skipped: number
}

export interface ImportCounts {
  rows?: number
  blocking_errors?: number
  error_rows?: number
  warnings?: number
  undecided_duplicates?: number
  importable?: number
  skipped_rows?: number
  skipped_blank?: number
  skipped_repeated_header?: number
  by_section?: Record<string, Record<string, number>>
  committed?: CommittedCounts
}

export interface ImportJobSummary {
  public_id: string
  profile_code: string
  profile_version: number
  status: ImportStatus
  original_filename: string
  file_size: number
  uploaded_by: AuditActor | null
  uploaded_at: string
  validated_at: string | null
  committed_at: string | null
  finished_at: string | null
  counts: ImportCounts
}

export interface ImportJob extends ImportJobSummary {
  file_sha256: string
  file_stored: boolean
  workbook: WorkbookSheet[]
  column_mapping: MappingSection[]
  mapping_confirmed: boolean
  previously_imported_by: string[]
  failure_code: string | null
  validated_by: AuditActor | null
  committed_by: AuditActor | null
  version: number
}

export interface ImportIssue {
  id: number
  section: string | null
  sheet: string | null
  row_number: number | null
  column: string | null
  field: string | null
  code: string
  severity: IssueSeverity
  source_value: string | null
  params: Record<string, unknown> | null
}

export interface ImportRow {
  id: number
  section: string
  sheet: string
  row_number: number
  outcome: string
  values: Record<string, unknown>
  source: Record<string, unknown>
  changes: Record<string, { from: unknown; to: unknown; effective_date?: string }> | null
  decision: RowDecision | null
  decision_reason: string | null
  target_public_id: string | null
  issues: ImportIssue[]
}

export interface MappingSuggestion {
  public_id: string
  code: string
  label: string
  score: number
  reason: string
}

export interface ValueMapping {
  public_id: string
  kind: string
  source_text: string
  normalised_text: string
  status: MappingStatus
  target: Ref | null
  decision_reason: string | null
  decided_by: AuditActor | null
  decided_at: string | null
  created_at: string
  suggestions: MappingSuggestion[]
  version: number
}

export interface JobFilters {
  status?: ImportStatus
  profile?: string
}

export interface RowFilters {
  section?: string
  outcome?: RowOutcome
}

export interface IssueFilters {
  severity?: IssueSeverity
  code?: string
}

export interface MappingFilters {
  kind?: MappingKind
  status?: MappingStatus
}

/** A file to save (template or error report). */
export interface Download {
  blob: Blob
  filename: string
}
