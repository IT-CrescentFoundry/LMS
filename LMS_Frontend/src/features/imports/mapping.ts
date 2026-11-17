import type { ImportProfile, MappingSection, ProfileSection, WorkbookSheet } from '../../types/imports'

/**
 * Same comparison form as `normalise_label` in
 * LMS_Backend/app/services/imports/profiles.py: deterministic, never fuzzy.
 */
export function normaliseLabel(text: string): string {
  return text
    .normalize('NFKC')
    .toLocaleLowerCase('en')
    .replace(/&/g, ' and ')
    .replace(/[\s_]+/g, ' ')
    .replace(/[.,:;()[\]#*]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** The field whose name or alias equals the header exactly (after normalisation). */
export function suggestField(section: ProfileSection, header: string): string | null {
  const label = normaliseLabel(header)
  if (!label) return null
  for (const field of section.fields) {
    if (
      label === normaliseLabel(field.name.replace(/_/g, ' ')) ||
      field.aliases.some((alias) => label === normaliseLabel(alias))
    ) {
      return field.name
    }
  }
  return null
}

/** Suggested columns for a sheet mapped as `section` (excluded columns never). */
export function suggestColumns(sheet: WorkbookSheet, section: ProfileSection): Record<string, string> {
  const columns: Record<string, string> = {}
  const used = new Set<string>()
  for (const header of sheet.headers) {
    if (header.excluded) continue
    const field = suggestField(section, header.text)
    if (field && !used.has(field)) {
      columns[String(header.index)] = field
      used.add(field)
    }
  }
  return columns
}

export interface SectionProblems {
  missing: string[]
  twice: string[]
  noHeader: boolean
}

export function sectionProblems(
  mapping: MappingSection,
  profile: ImportProfile,
  sheets: readonly WorkbookSheet[],
): SectionProblems {
  const spec = profile.sections.find((section) => section.kind === mapping.section)
  const sheet = sheets.find((item) => item.name === mapping.sheet)
  const chosen = Object.values(mapping.columns)
  const twice = [...new Set(chosen.filter((field, index) => chosen.indexOf(field) !== index))]
  const missing = (spec?.fields ?? [])
    .filter((field) => field.required && !chosen.includes(field.name))
    .map((field) => field.name)
  return { missing, twice, noHeader: !sheet || sheet.header_row === null }
}

export function hasProblems(problems: SectionProblems): boolean {
  return problems.noHeader || problems.missing.length > 0 || problems.twice.length > 0
}

/** A new section for the first sheet with a header row, with suggested columns. */
export function newSection(profile: ImportProfile, sheets: readonly WorkbookSheet[], kind?: string): MappingSection | null {
  const sheet = sheets.find((item) => item.header_row !== null && item.state === 'visible') ??
    sheets.find((item) => item.header_row !== null)
  const spec = profile.sections.find((section) => section.kind === kind) ?? profile.sections[0]
  if (!sheet || sheet.header_row === null || !spec) return null
  return { section: spec.kind, sheet: sheet.name, header_row: sheet.header_row, columns: suggestColumns(sheet, spec) }
}

/** Re-targets a section to another sheet or kind, re-suggesting its columns. */
export function retarget(
  mapping: MappingSection,
  profile: ImportProfile,
  sheets: readonly WorkbookSheet[],
  change: { sheet?: string; section?: string },
): MappingSection {
  const sheetName = change.sheet ?? mapping.sheet
  const kind = change.section ?? mapping.section
  const sheet = sheets.find((item) => item.name === sheetName)
  const spec = profile.sections.find((section) => section.kind === kind)
  return {
    section: kind,
    sheet: sheetName,
    header_row: sheet?.header_row ?? mapping.header_row,
    columns: sheet && spec ? suggestColumns(sheet, spec) : {},
  }
}

/** Values shown first on a row card (the natural key), then everything else mapped. */
const KEY_FIELDS = ['employee_code', 'full_name', 'unit', 'manager_code', 'effective_from']

/**
 * The server adds how each reference was resolved (`<field>_id`, `<field>_method`) to
 * the staged values; that is bookkeeping, not workbook data, and is not shown.
 */
export function shownFields(values: Record<string, unknown>): string[] {
  const keys = Object.keys(values).filter((key) => {
    const base = key.replace(/_(id|method)$/, '')
    return base === key || !(base in values)
  })
  return [...KEY_FIELDS.filter((field) => keys.includes(field)), ...keys.filter((field) => !KEY_FIELDS.includes(field))]
}
