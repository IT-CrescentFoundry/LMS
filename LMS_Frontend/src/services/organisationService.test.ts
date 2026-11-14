import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, setCsrfToken } from '../lib/apiClient'
import { formatDate, parseIsoDate } from '../lib/format'
import { orgUnit, SUB_NODE, tree, treeNode } from '../test/orgFixtures'
import { mockApi, reply } from '../test/renderApp'
import { organisationService, parseOrgUnit, parseTree, translationChanges } from './organisationService'

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken(null)
})

describe('organisation parsers', () => {
  it('keeps only known fields and supported translation locales', () => {
    const parsed = parseOrgUnit({
      ...orgUnit(SUB_NODE),
      translations: { hi: 'परीक्षण', fr: 'Essai', bn: '' },
      password_hash: 'never-shown',
    })
    expect(parsed.translations).toEqual({ hi: 'परीक्षण' })
    expect('password_hash' in parsed).toBe(false)
  })

  it('rejects malformed business dates and unknown statuses', () => {
    expect(() => parseTree(tree([treeNode('u', 'U', 'Unit')], '14/11/2026'))).toThrow(/as_of/)
    expect(() => parseTree(tree([treeNode('u', 'U', 'Unit', { status: 'deleted' })]))).toThrow(/status/)
  })

  it('formats business dates without a time-zone shift', () => {
    expect(parseIsoDate('2026-01-31')?.getDate()).toBe(31)
    expect(parseIsoDate('2026-13-01x')).toBeUndefined()
    expect(formatDate('not-a-date', 'en')).toBe('not-a-date')
  })
})

describe('translationChanges', () => {
  it('reports only changed locales, removing blanks', () => {
    expect(translationChanges({ bn: 'ক', hi: 'ख' }, { bn: 'ক', hi: '  ', gu: 'ગ' })).toEqual({ hi: null, gu: 'ગ' })
    expect(translationChanges({ bn: 'ক' }, { bn: ' ক ' })).toBeUndefined()
  })
})

describe('organisation requests', () => {
  it('sends writes with the CSRF token and reads the tree with filters', async () => {
    const api = mockApi({
      'GET /org/tree': reply(tree([])),
      'POST /org/units/u-1/close': reply({ unit: orgUnit(SUB_NODE), warnings: [] }),
    })
    setCsrfToken('csrf-xyz')
    await organisationService.getTree({ as_of: '2026-03-31', include_closed: true })
    expect(Object.fromEntries(api.requestsTo('GET /org/tree')[0].query)).toEqual({
      as_of: '2026-03-31',
      include_closed: 'true',
    })
    await organisationService.closeUnit('u-1', { version: 3, effective_date: '2026-12-31', reason: null })
    const close = api.requestsTo('POST /org/units/u-1/close')[0]
    expect(close.headers['x-csrf-token']).toBe('csrf-xyz')
    expect(close.body).toEqual({ version: 3, effective_date: '2026-12-31', reason: null })
  })

  it('surfaces blockers from a refused closure', async () => {
    mockApi({
      'POST /org/units/u-1/close': reply(
        {
          error: {
            code: 'unit_has_dependants',
            message: 'x',
            details: [{ location: ['children', 'TEST_A'], message: 'x', type: 'active_child' }],
          },
        },
        409,
      ),
    })
    const error = await organisationService
      .closeUnit('u-1', { version: 1, effective_date: '2026-12-31' })
      .catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).details).toEqual([{ location: ['children', 'TEST_A'], message: 'x', type: 'active_child' }])
  })
})
