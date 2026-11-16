import { describe, expect, it } from 'vitest'

import { resources } from '../../i18n'
import { ApiError } from '../../lib/apiClient'
import { EMPLOYEE_EVENT_TYPES, DATA_QUALITY_CHECKS, STATUS_FILTERS } from '../../types/employee'
import { describeEmployeeError, EMPLOYEE_ERROR_CODES, SEPARATION_BLOCKER_TYPES } from './employeeErrors'

function apiError(code: string, details: { location: string[]; message: string; type: string }[] = []) {
  return new ApiError('http', 'refused', { status: 409, code, requestId: 'req-9', details })
}

describe('employee error descriptions', () => {
  it('lists separation blockers with what the API names', () => {
    const described = describeEmployeeError(
      apiError('open_records_on_separation', [
        { location: ['direct_report', 'T-SUB'], message: 'x', type: 'open_direct_report' },
        { location: ['assignment', 'OPERATION'], message: 'x', type: 'open_assignment' },
        { location: ['future_thing', 'X1'], message: 'x', type: 'something_new' },
      ]),
    )
    expect(described).toEqual({
      kind: 'code',
      code: 'open_records_on_separation',
      requestId: 'req-9',
      blockers: [
        { type: 'open_direct_report', rawType: 'open_direct_report', label: 'T-SUB' },
        { type: 'open_assignment', rawType: 'open_assignment', label: 'OPERATION' },
        { type: 'other', rawType: 'something_new', label: 'X1' },
      ],
    })
  })

  it('never hides an unknown code behind a generic message', () => {
    expect(describeEmployeeError(apiError('brand_new_rule'))).toEqual({
      kind: 'unknown_code',
      code: 'brand_new_rule',
      requestId: 'req-9',
    })
  })

  it('classifies network failures', () => {
    expect(describeEmployeeError(new ApiError('network', 'down'))).toEqual({ kind: 'network' })
  })
})

describe('employee translations', () => {
  const keys = [
    ...EMPLOYEE_ERROR_CODES.map((code) => `emp.errors.codes.${code}`),
    ...SEPARATION_BLOCKER_TYPES.map((type) => `emp.errors.blockers.${type}`),
    ...EMPLOYEE_EVENT_TYPES.map(([, label]) => `emp.history.events.${label}`),
    ...STATUS_FILTERS.map((status) => `emp.status.${status}`),
    'org.errors.blockers.employee_assignment',
    'org.errors.blockers.employee_responsibility',
    'auth.errors.employeeHasActiveAccount',
  ]

  function lookup(language: keyof typeof resources, key: string): unknown {
    return key
      .split('.')
      .reduce<unknown>(
        (node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined),
        resources[language].common,
      )
  }

  it('has every code, blocker, event and status in English', () => {
    for (const key of keys) expect(typeof lookup('en', key), key).toBe('string')
  })

  it.each(['bn', 'hi', 'gu'] as const)('translates every code, blocker, event and status into %s', (language) => {
    for (const key of keys) {
      const translated = lookup(language, key)
      expect(typeof translated, `${language}: ${key}`).toBe('string')
      expect(translated, `${language}: ${key}`).not.toBe(lookup('en', key))
    }
  })

  it('keeps the data-quality check list stable (eight backend checks)', () => {
    expect(DATA_QUALITY_CHECKS).toHaveLength(8)
  })

  it.each(['bn', 'hi', 'gu'] as const)('translates every employee-area string into %s (no English fallback)', (language) => {
    const flatten = (node: unknown, prefix: string): [string, string][] =>
      typeof node === 'string'
        ? [[prefix, node]]
        : Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => flatten(v, `${prefix}.${k}`))
    const theirs = new Map(flatten(resources[language].common.emp, 'emp'))
    const english = flatten(resources.en.common.emp, 'emp')
    expect(english.length).toBeGreaterThan(400)
    for (const [key, text] of english) {
      expect(theirs.get(key), `${language}: ${key}`).toBeDefined()
      expect(theirs.get(key), `${language}: ${key}`).not.toBe(text)
    }
    // Plural forms come in complete pairs.
    for (const [key] of english.filter(([k]) => k.endsWith('_one'))) {
      expect(theirs.has(key.replace(/_one$/, '_other')), `${language}: ${key}`).toBe(true)
    }
    expect(resources[language].common.nav.employees).not.toBe(resources.en.common.nav.employees)
  })

  it('describes all eight data-quality checks and keeps the separation label', () => {
    const checks = resources.en.common.emp.dataQuality.checks
    expect(Object.keys(checks).sort()).toEqual([...DATA_QUALITY_CHECKS].sort())
    for (const code of DATA_QUALITY_CHECKS) {
      expect(checks[code].title.length, code).toBeGreaterThan(3)
      expect(checks[code].description.length, code).toBeGreaterThan(10)
    }
    expect(resources.en.common.emp.separation.lastWorkingDay).toBe('Last Working Day')
  })
})

