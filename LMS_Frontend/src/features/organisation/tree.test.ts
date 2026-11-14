import { describe, expect, it } from 'vitest'

import { BASELINE_NODES, CLOSED_NODE, DEPT_NODE, SUB_NODE, treeNode } from '../../test/orgFixtures'
import type { TreeNode } from '../../types/organisation'
import { localName, textMatches } from './names'
import {
  ancestorIds,
  buildTreeIndex,
  descendantIds,
  isFilterActive,
  matchingIds,
  visibleRows,
  withAncestors,
} from './tree'

const nodes = [...BASELINE_NODES, SUB_NODE, DEPT_NODE, CLOSED_NODE] as TreeNode[]
const index = buildTreeIndex(nodes, 'en')
const noFilter = { query: '', unitTypeId: '', statusView: 'active' as const }

describe('organisation tree helpers', () => {
  it('rebuilds the hierarchy with the five functions at the top, ordered by name', () => {
    const roots = index.children.get(null)?.map((node) => node.name)
    expect(roots).toEqual(['Accounts & Commercial', 'HR, Admin & IT', 'Operation', 'Purchase', 'Sales & BD'])
    expect(index.children.get('unit-ops')?.map((node) => node.code)).toEqual(['TEST_MELT', 'TEST_OLD'])
  })

  it('treats a unit whose parent is not listed as top level (never hides it)', () => {
    const orphan = treeNode('unit-x', 'X', 'Orphan', { parent_id: 'missing' }) as TreeNode
    const withOrphan = buildTreeIndex([...nodes, orphan], 'en')
    expect(withOrphan.children.get(null)?.some((node) => node.public_id === 'unit-x')).toBe(true)
  })

  it('finds ancestors and descendants', () => {
    expect(ancestorIds(index, 'unit-furnace')).toEqual(['unit-ops', 'unit-melt'])
    expect(ancestorIds(index, 'unit-ops')).toEqual([])
    expect([...descendantIds(index, 'unit-ops')].sort()).toEqual(['unit-furnace', 'unit-melt', 'unit-old'])
  })

  it('flattens only expanded branches, with ARIA position data', () => {
    const collapsed = visibleRows(index, new Set(), null)
    expect(collapsed.map((row) => row.node.code)).toEqual(['ACC_COM', 'HR_ADMIN_IT', 'OPERATION', 'PURCHASE', 'SALES_BD'])
    const ops = collapsed[2]
    expect(ops).toMatchObject({ level: 1, posInSet: 3, setSize: 5, hasChildren: true, expanded: false })

    const open = visibleRows(index, new Set(['unit-ops', 'unit-melt']), null)
    expect(open.map((row) => `${row.level}:${row.node.code}`)).toEqual([
      '1:ACC_COM',
      '1:HR_ADMIN_IT',
      '1:OPERATION',
      '2:TEST_MELT',
      '3:TEST_FURNACE',
      '2:TEST_OLD',
      '1:PURCHASE',
      '1:SALES_BD',
    ])
  })

  it('matches by name, code and translated name, keeping ancestors for context', () => {
    expect(isFilterActive(noFilter)).toBe(false)
    expect(matchingIds(index, noFilter)).toBeNull()

    const byName = matchingIds(index, { ...noFilter, query: 'furnace' }, 'en')
    expect([...(byName ?? [])]).toEqual(['unit-furnace'])
    expect([...withAncestors(index, byName ?? new Set())].sort()).toEqual(['unit-furnace', 'unit-melt', 'unit-ops'])

    expect([...(matchingIds(index, { ...noFilter, query: 'hr_admin' }, 'en') ?? [])]).toEqual(['unit-hr'])
    expect([...(matchingIds(index, { ...noFilter, query: 'पिघलन' }, 'hi') ?? [])]).toEqual(['unit-melt'])
  })

  it('filters by unit type and status', () => {
    const departments = matchingIds(index, { ...noFilter, unitTypeId: 'type-dept' })
    expect([...(departments ?? [])].sort()).toEqual(['unit-furnace', 'unit-old'])
    const closed = matchingIds(index, { ...noFilter, statusView: 'closed' })
    expect([...(closed ?? [])]).toEqual(['unit-old'])
    expect(isFilterActive({ ...noFilter, statusView: 'all' })).toBe(false)
  })
})

describe('display names', () => {
  it('uses the translation for the UI language and falls back to the recorded name', () => {
    const unit = { name: 'Test Melting', translations: { hi: 'परीक्षण पिघलन' } }
    expect(localName(unit, 'hi')).toBe('परीक्षण पिघलन')
    expect(localName(unit, 'bn')).toBe('Test Melting')
    expect(localName(unit, 'en')).toBe('Test Melting')
  })

  it('searches case- and accent-insensitively', () => {
    expect(textMatches(['Sales & BD'], 'sales')).toBe(true)
    expect(textMatches(['Café'], 'cafe')).toBe(true)
    expect(textMatches(['Purchase', null], 'xyz')).toBe(false)
    expect(textMatches(['anything'], '  ')).toBe(true)
  })
})
