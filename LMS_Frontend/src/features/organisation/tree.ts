/**
 * Pure helpers for the organisation tree (no React). The API returns a flat node
 * list for one date (`GET /org/tree`); the hierarchy is rebuilt here.
 */

import type { TreeNode, UnitStatus } from '../../types/organisation'
import { localName, textMatches } from './names'

export interface TreeIndex {
  byId: ReadonlyMap<string, TreeNode>
  /** Children by parent id; top-level units are under `null`. */
  children: ReadonlyMap<string | null, readonly TreeNode[]>
}

/**
 * Builds the hierarchy. A node whose parent is not in the list (e.g. a parent that
 * is not shown on this date) is treated as top level, so no unit is ever hidden.
 * Siblings are ordered by display name, then code.
 */
export function buildTreeIndex(nodes: readonly TreeNode[], language?: string): TreeIndex {
  const byId = new Map(nodes.map((node) => [node.public_id, node]))
  const children = new Map<string | null, TreeNode[]>()
  for (const node of nodes) {
    const parent = node.parent_id !== null && byId.has(node.parent_id) ? node.parent_id : null
    const list = children.get(parent) ?? []
    list.push(node)
    children.set(parent, list)
  }
  const collator = new Intl.Collator(language, { sensitivity: 'base', numeric: true })
  for (const list of children.values()) {
    list.sort(
      (a, b) =>
        collator.compare(localName(a, language), localName(b, language)) ||
        a.code.localeCompare(b.code),
    )
  }
  return { byId, children }
}

export function parentIdOf(index: TreeIndex, id: string): string | null {
  const parent = index.byId.get(id)?.parent_id ?? null
  return parent !== null && index.byId.has(parent) ? parent : null
}

/** Ancestors of `id`, from the top-level unit down to its parent. */
export function ancestorIds(index: TreeIndex, id: string): string[] {
  const path: string[] = []
  const seen = new Set([id])
  let current = parentIdOf(index, id)
  while (current !== null && !seen.has(current)) {
    path.unshift(current)
    seen.add(current)
    current = parentIdOf(index, current)
  }
  return path
}

/** All units below `id` (used to keep a unit from being moved under itself). */
export function descendantIds(index: TreeIndex, id: string): Set<string> {
  const result = new Set<string>()
  const stack = [...(index.children.get(id) ?? [])]
  while (stack.length > 0) {
    const node = stack.pop()
    if (!node || result.has(node.public_id)) continue
    result.add(node.public_id)
    stack.push(...(index.children.get(node.public_id) ?? []))
  }
  return result
}

/**
 * Which units to show. `active` asks the API for active units only; the other
 * views include closed units (`include_closed`), and `closed` / `not_started` then
 * keep only units with that status on the selected date.
 */
export const STATUS_VIEWS = ['active', 'all', 'closed', 'not_started'] as const
export type StatusView = (typeof STATUS_VIEWS)[number]

export interface TreeFilter {
  query: string
  unitTypeId: string
  statusView: StatusView
}

export function isFilterActive(filter: TreeFilter): boolean {
  return (
    filter.query.trim() !== '' ||
    filter.unitTypeId !== '' ||
    filter.statusView === 'closed' ||
    filter.statusView === 'not_started'
  )
}

function statusFor(view: StatusView): UnitStatus | null {
  return view === 'closed' || view === 'not_started' ? view : null
}

/** Units matching the filter, or null when no filter is active. */
export function matchingIds(index: TreeIndex, filter: TreeFilter, language?: string): Set<string> | null {
  if (!isFilterActive(filter)) return null
  const status = statusFor(filter.statusView)
  const result = new Set<string>()
  for (const node of index.byId.values()) {
    if (filter.unitTypeId && node.unit_type.public_id !== filter.unitTypeId) continue
    if (status && node.status !== status) continue
    const names = [node.name, node.code, node.short_name, localName(node, language), ...Object.values(node.translations)]
    if (!textMatches(names, filter.query)) continue
    result.add(node.public_id)
  }
  return result
}

/** Matches plus their ancestors (shown for context). */
export function withAncestors(index: TreeIndex, ids: ReadonlySet<string>): Set<string> {
  const result = new Set(ids)
  for (const id of ids) for (const ancestor of ancestorIds(index, id)) result.add(ancestor)
  return result
}

export interface TreeRow {
  node: TreeNode
  level: number
  posInSet: number
  setSize: number
  hasChildren: boolean
  expanded: boolean
}

function visibleChildren(
  index: TreeIndex,
  parent: string | null,
  visible: ReadonlySet<string> | null,
): readonly TreeNode[] {
  const all = index.children.get(parent) ?? []
  return visible ? all.filter((node) => visible.has(node.public_id)) : all
}

/** The rows currently displayed, in order (expanded branches only). */
export function visibleRows(
  index: TreeIndex,
  expanded: ReadonlySet<string>,
  visible: ReadonlySet<string> | null,
): TreeRow[] {
  const rows: TreeRow[] = []
  const walk = (parent: string | null, level: number) => {
    const siblings = visibleChildren(index, parent, visible)
    siblings.forEach((node, position) => {
      const hasChildren = visibleChildren(index, node.public_id, visible).length > 0
      const isExpanded = hasChildren && expanded.has(node.public_id)
      rows.push({
        node,
        level,
        posInSet: position + 1,
        setSize: siblings.length,
        hasChildren,
        expanded: isExpanded,
      })
      if (isExpanded) walk(node.public_id, level + 1)
    })
  }
  walk(null, 1)
  return rows
}

export function childCount(index: TreeIndex, id: string | null, visible: ReadonlySet<string> | null): number {
  return visibleChildren(index, id, visible).length
}

export { visibleChildren }
