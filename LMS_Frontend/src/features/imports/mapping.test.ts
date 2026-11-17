import { describe, expect, it } from 'vitest'

import { PROFILE, WORKBOOK } from '../../test/importFixtures'
import type { ImportProfile, WorkbookSheet } from '../../types/imports'
import { normaliseLabel, retarget, sectionProblems, shownFields, suggestColumns, suggestField } from './mapping'

const profile = PROFILE as ImportProfile
const sheets = WORKBOOK as WorkbookSheet[]
const employees = profile.sections[0]

describe('header suggestions (same rules as the server)', () => {
  it('normalises case, spacing, punctuation and ampersands only', () => {
    expect(normaliseLabel('  EMP. CODE ')).toBe('emp code')
    expect(normaliseLabel('Sales & BD')).toBe('sales and bd')
    expect(normaliseLabel('Date_of_Joining')).toBe('date of joining')
  })

  it('suggests exact alias matches and never guesses', () => {
    expect(suggestField(employees, 'Emp Code')).toBe('employee_code')
    expect(suggestField(employees, 'full name')).toBe('full_name')
    expect(suggestField(employees, 'Employe Code')).toBeNull()
    expect(suggestField(employees, '')).toBeNull()
  })

  it('never suggests excluded columns', () => {
    expect(suggestColumns(sheets[0], employees)).toEqual({ '1': 'employee_code', '2': 'full_name', '4': 'date_of_joining' })
  })
})

describe('mapping checks', () => {
  it('reports missing required and duplicated fields', () => {
    const problems = sectionProblems(
      { section: 'employees', sheet: 'Employees', header_row: 1, columns: { '1': 'employee_code', '4': 'employee_code' } },
      profile,
      sheets,
    )
    expect(problems).toEqual({ missing: ['full_name'], twice: ['employee_code'], noHeader: false })
  })

  it('re-suggests columns when a section is re-targeted', () => {
    const moved = retarget(
      { section: 'employees', sheet: 'Employees', header_row: 1, columns: { '1': 'employee_code' } },
      profile,
      sheets,
      { section: 'assignments' },
    )
    // "Emp Code" is not an alias of the assignments field in this profile: no guess.
    expect(moved).toEqual({ section: 'assignments', sheet: 'Employees', header_row: 1, columns: {} })
  })
})

describe('row cards', () => {
  it('show workbook fields, never the reference-resolution bookkeeping of the server', () => {
    expect(
      shownFields({
        designation: 'E2E_OPR',
        designation_id: '01900000-0000-7000-8000-00000000f001',
        designation_method: 'code',
        unit: 'E2E_MELT',
        unit_id: '01900000-0000-7000-8000-00000000f002',
        unit_method: 'code',
        employee_code: '00101',
        effective_from: '2025-04-01',
      }),
    ).toEqual(['employee_code', 'unit', 'effective_from', 'designation'])
  })

  it('keeps a real field whose name ends in _id when there is no matching base field', () => {
    expect(shownFields({ external_id: 'X-1' })).toEqual(['external_id'])
  })
})
