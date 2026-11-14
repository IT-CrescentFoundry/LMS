import { ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { localName } from './names'
import { UnitStatusBadge } from './OrgParts'
import { ancestorIds, childCount, visibleChildren, type TreeIndex } from './tree'

interface MobileUnitBrowserProps {
  index: TreeIndex
  /** Units to show (matches and their ancestors) when a filter is active. */
  visible: ReadonlySet<string> | null
  matches: ReadonlySet<string> | null
  parentId: string | null
  onParentChange: (id: string | null) => void
  onSelect: (id: string) => void
  typeName: (typeId: string, fallback: string) => string
}

/**
 * Drill-down navigation for narrow screens: one level at a time, with a trail
 * back to the top. While searching, matching units are listed with their path.
 */
export function MobileUnitBrowser({
  index,
  visible,
  matches,
  parentId,
  onParentChange,
  onSelect,
  typeName,
}: MobileUnitBrowserProps) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage

  if (matches !== null) {
    const results = [...matches].map((id) => index.byId.get(id)).filter((node) => node !== undefined)
    if (results.length === 0) return null
    return (
      <ul aria-label={t('org.structure.tree.label')} className="divide-y divide-slate-100">
        {results.map((node) => (
          <li key={node.public_id}>
            <button
              type="button"
              onClick={() => onSelect(node.public_id)}
              className="w-full px-3 py-3 text-left hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <span className="block font-medium break-words text-slate-900">{localName(node, language)}</span>
              <span className="block text-xs break-words text-slate-500">
                {[...ancestorIds(index, node.public_id).map((id) => localName(index.byId.get(id)!, language))]
                  .join(' › ') || t('org.common.topLevel')}
              </span>
            </button>
          </li>
        ))}
      </ul>
    )
  }

  const trail = parentId === null ? [] : [...ancestorIds(index, parentId), parentId]
  const items = visibleChildren(index, parentId, visible)

  return (
    <div className="space-y-2">
      <nav aria-label={t('org.structure.drill.trail')}>
        <ol className="flex flex-wrap items-center gap-1 px-3 pt-3 text-sm">
          <li>
            <button
              type="button"
              onClick={() => onParentChange(null)}
              aria-current={parentId === null ? 'location' : undefined}
              className="rounded font-medium text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              {t('org.structure.drill.top')}
            </button>
          </li>
          {trail.map((id) => (
            <li key={id} className="flex items-center gap-1">
              <ChevronRight aria-hidden="true" className="size-4 text-slate-400" />
              <button
                type="button"
                onClick={() => onParentChange(id)}
                aria-current={id === parentId ? 'location' : undefined}
                className="rounded break-words text-brand-700 hover:underline focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                {localName(index.byId.get(id)!, language)}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <ul aria-label={t('org.structure.tree.label')} className="divide-y divide-slate-100">
        {items.map((node) => {
          const count = childCount(index, node.public_id, visible)
          const name = localName(node, language)
          return (
            <li key={node.public_id} className="flex items-stretch">
              <button
                type="button"
                onClick={() => onSelect(node.public_id)}
                className="min-w-0 flex-1 px-3 py-3 text-left hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                <span className="block font-medium break-words text-slate-900">{name}</span>
                <span className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="font-mono">{node.code}</span>
                  <span>{typeName(node.unit_type.public_id, node.unit_type.name)}</span>
                  {node.status !== 'active' ? <UnitStatusBadge status={node.status} /> : null}
                </span>
              </button>
              {count > 0 ? (
                <button
                  type="button"
                  onClick={() => onParentChange(node.public_id)}
                  aria-label={t('org.structure.drill.open', { name, count })}
                  className="flex shrink-0 items-center gap-1 px-3 text-sm text-brand-700 hover:bg-brand-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                >
                  <span aria-hidden="true">{count}</span>
                  <ChevronRight aria-hidden="true" className="size-5" />
                </button>
              ) : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
