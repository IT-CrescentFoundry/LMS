import { ChevronDown, ChevronRight, MapPin } from 'lucide-react'
import { useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { inputClassName, labelClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import type { TreeNode } from '../../types/organisation'
import { AdminErrorState } from '../admin/AdminParts'
import { localName } from './names'
import { useOrgTree } from './orgQueries'
import { buildForest } from './chart'

interface ChartNode {
  node: TreeNode
  children: ChartNode[]
}

function matches(entry: ChartNode, q: string): boolean {
  return `${entry.node.name} ${entry.node.code}`.toLowerCase().includes(q)
}

function subtreeMatches(entry: ChartNode, q: string): boolean {
  return matches(entry, q) || entry.children.some((child) => subtreeMatches(child, q))
}

/**
 * Organisation chart: the current structure drawn top-down as cards (type, code, name),
 * collapsible per unit, horizontally scrollable. Search highlights matching units and
 * keeps their ancestors expanded.
 */
export function OrgChartPage() {
  const { t, i18n } = useTranslation()
  const tree = useOrgTree({})
  const forest = useMemo(() => buildForest(tree.data?.nodes ?? []), [tree.data])
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [q, setQ] = useState('')
  const searchId = useId()
  const query = q.trim().toLowerCase()

  if (tree.isPending) return <LoadingState />
  if (tree.isError) return <AdminErrorState error={tree.error} title={t('org.chart.loadError')} onRetry={() => void tree.refetch()} isRetrying={tree.isFetching} />

  const toggle = (id: string) =>
    setCollapsed((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const render = (entry: ChartNode) => {
    const id = entry.node.public_id
    const open = query ? subtreeMatches(entry, query) : !collapsed.has(id)
    const hit = query !== '' && matches(entry, query)
    const visibleChildren = query ? entry.children.filter((child) => subtreeMatches(child, query)) : entry.children
    return (
      <li key={id} className="org-chart-node">
        <div
          className={`inline-flex min-w-40 flex-col items-center rounded-lg border bg-white px-3 py-2 text-center shadow-sm ${
            hit ? 'border-gold-500 ring-2 ring-gold-300' : 'border-slate-200'
          } ${entry.node.status === 'closed' ? 'opacity-60' : ''}`}
        >
          <span className="text-[11px] font-medium tracking-wide text-slate-500 uppercase">{entry.node.unit_type.name}</span>
          <span className="font-semibold text-slate-900">{localName(entry.node, i18n.resolvedLanguage)}</span>
          <span className="font-mono text-xs text-slate-500">{entry.node.code}</span>
          {entry.node.location ? (
            <span className="mt-0.5 inline-flex items-center gap-1 text-xs text-slate-600">
              <MapPin aria-hidden="true" className="size-3" />
              {entry.node.location.name}
            </span>
          ) : null}
          <span className="mt-1 flex gap-2">
            {entry.children.length > 0 ? (
              <button
                type="button"
                onClick={() => toggle(id)}
                aria-expanded={open}
                aria-label={t(open ? 'org.chart.collapse' : 'org.chart.expand', { name: entry.node.name })}
                className="inline-flex items-center gap-0.5 rounded px-1 text-xs text-brand-700 hover:bg-brand-50"
              >
                {open ? <ChevronDown aria-hidden="true" className="size-3.5" /> : <ChevronRight aria-hidden="true" className="size-3.5" />}
                {t('org.chart.children', { count: entry.children.length })}
              </button>
            ) : null}
            <Link to={`/employees?unit=${encodeURIComponent(id)}`} className="rounded px-1 text-xs text-brand-700 hover:underline">
              {t('org.chart.employees')}
            </Link>
          </span>
        </div>
        {open && visibleChildren.length > 0 ? <ul>{visibleChildren.map(render)}</ul> : null}
      </li>
    )
  }

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">{t('org.chart.title')}</h1>
        <p className="max-w-3xl text-slate-600">{t('org.chart.subtitle')}</p>
      </header>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 space-y-1.5 sm:max-w-sm">
          <label htmlFor={searchId} className={labelClassName}>
            {t('org.chart.search')}
          </label>
          <input id={searchId} type="search" value={q} onChange={(e) => setQ(e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <button type="button" onClick={() => setCollapsed(new Set())} className={secondaryButtonClassName}>
          {t('org.chart.expandAll')}
        </button>
        <button type="button" onClick={() => setCollapsed(new Set(forest.flatMap(function ids(e): string[] { return [e.node.public_id, ...e.children.flatMap(ids)] })))} className={secondaryButtonClassName}>
          {t('org.chart.collapseAll')}
        </button>
      </div>
      {forest.length === 0 ? (
        <p className="text-sm text-slate-600">{t('org.chart.empty')}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4" role="region" aria-label={t('org.chart.title')} tabIndex={0}>
          <ul className="org-chart" aria-label={t('org.chart.treeLabel')}>
            {forest.map(render)}
          </ul>
        </div>
      )}
    </div>
  )
}
