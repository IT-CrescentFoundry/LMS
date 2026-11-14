import { ChevronRight } from 'lucide-react'
import { useEffect, useRef, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { localName } from './names'
import { UnitStatusBadge } from './OrgParts'
import type { TreeRow } from './tree'

interface OrgTreeProps {
  label: string
  rows: readonly TreeRow[]
  selectedId: string | null
  focusedId: string | null
  onFocusChange: (id: string) => void
  onSelect: (id: string) => void
  onToggle: (id: string, expand: boolean) => void
  /** Ids whose label matched the search (highlighted). */
  matches: ReadonlySet<string> | null
  /** Display name of a unit type (translated when available). */
  typeName: (typeId: string, fallback: string) => string
}

/**
 * Keyboard-accessible tree (WAI-ARIA tree view pattern). One item is in the tab
 * order at a time (roving tabindex):
 *   Up / Down       previous / next visible unit
 *   Right           expand, or move to the first child
 *   Left            collapse, or move to the parent
 *   Home / End      first / last visible unit
 *   Enter / Space   show the unit's details
 * The chevron can also be clicked; nothing depends on drag and drop.
 */
export function OrgTree({
  label,
  rows,
  selectedId,
  focusedId,
  onFocusChange,
  onSelect,
  onToggle,
  matches,
  typeName,
}: OrgTreeProps) {
  const { i18n } = useTranslation()
  const itemRefs = useRef(new Map<string, HTMLLIElement>())
  const hasFocusRef = useRef(false)
  const language = i18n.resolvedLanguage

  const activeId =
    focusedId !== null && rows.some((row) => row.node.public_id === focusedId)
      ? focusedId
      : (selectedId !== null && rows.some((row) => row.node.public_id === selectedId) ? selectedId : rows[0]?.node.public_id) ?? null

  // Keep DOM focus on the active item while the tree has focus (e.g. after expanding).
  useEffect(() => {
    if (hasFocusRef.current && activeId !== null) itemRefs.current.get(activeId)?.focus()
  }, [activeId])

  function move(index: number) {
    const row = rows[Math.max(0, Math.min(rows.length - 1, index))]
    if (row) onFocusChange(row.node.public_id)
  }

  function onKeyDown(event: KeyboardEvent<HTMLLIElement>, row: TreeRow, index: number) {
    let handled = true
    switch (event.key) {
      case 'ArrowDown':
        move(index + 1)
        break
      case 'ArrowUp':
        move(index - 1)
        break
      case 'Home':
        move(0)
        break
      case 'End':
        move(rows.length - 1)
        break
      case 'ArrowRight':
        if (row.hasChildren && !row.expanded) onToggle(row.node.public_id, true)
        else if (row.expanded) move(index + 1)
        break
      case 'ArrowLeft':
        if (row.expanded) onToggle(row.node.public_id, false)
        else {
          for (let i = index - 1; i >= 0; i -= 1) {
            if (rows[i].level === row.level - 1) {
              move(i)
              break
            }
          }
        }
        break
      case 'Enter':
      case ' ':
        onSelect(row.node.public_id)
        break
      default:
        handled = false
    }
    if (handled) {
      event.preventDefault()
      event.stopPropagation()
    }
  }

  return (
    <ul
      role="tree"
      aria-label={label}
      className="space-y-0.5"
      onFocus={() => {
        hasFocusRef.current = true
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) hasFocusRef.current = false
      }}
    >
      {rows.map((row, index) => {
        const { node } = row
        const id = node.public_id
        const name = localName(node, language)
        const selected = id === selectedId
        const matched = matches?.has(id) ?? false
        return (
          <li
            key={id}
            ref={(element) => {
              if (element) itemRefs.current.set(id, element)
              else itemRefs.current.delete(id)
            }}
            role="treeitem"
            aria-level={row.level}
            aria-setsize={row.setSize}
            aria-posinset={row.posInSet}
            aria-expanded={row.hasChildren ? row.expanded : undefined}
            aria-selected={selected}
            tabIndex={id === activeId ? 0 : -1}
            onKeyDown={(event) => onKeyDown(event, row, index)}
            onFocus={(event) => {
              if (event.target === event.currentTarget && id !== focusedId) onFocusChange(id)
            }}
            onClick={(event) => {
              event.stopPropagation()
              onFocusChange(id)
              onSelect(id)
            }}
            className={`flex cursor-pointer items-center gap-1 rounded-md py-1.5 pr-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none ${
              selected ? 'bg-brand-50 text-brand-900 ring-1 ring-brand-200' : 'text-slate-800 hover:bg-slate-100'
            }`}
            style={{ paddingLeft: `${0.25 + (row.level - 1) * 1.25}rem` }}
          >
            <span
              aria-hidden="true"
              onClick={(event) => {
                if (!row.hasChildren) return
                event.stopPropagation()
                onFocusChange(id)
                onToggle(id, !row.expanded)
              }}
              className={`inline-flex size-6 shrink-0 items-center justify-center rounded ${
                row.hasChildren ? 'text-slate-600 hover:bg-slate-200' : 'text-transparent'
              }`}
            >
              <ChevronRight className={`size-4 transition-transform ${row.expanded ? 'rotate-90' : ''}`} />
            </span>
            <span className="min-w-0 flex-1">
              <span className={`block break-words ${matched ? 'font-semibold' : 'font-medium'}`}>{name}</span>
              <span className="block text-xs text-slate-500">
                <span className="font-mono">{node.code}</span>
                <span aria-hidden="true"> · </span>
                <span className="sr-only">, </span>
                {typeName(node.unit_type.public_id, node.unit_type.name)}
              </span>
            </span>
            {node.status !== 'active' ? <UnitStatusBadge status={node.status} /> : null}
          </li>
        )
      })}
    </ul>
  )
}
