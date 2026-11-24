import {
  ArrowDown,
  ArrowUp,
  Check,
  CircleDashed,
  CircleHelp,
  ClipboardList,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'

import { tdClassName, thClassName } from '../../components/FeatureState'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import type { GapStatus, ItemStats, Level, MatrixCell, MatrixGrid, MatrixItem, MatrixRow, Risk } from '../../types/competency'
import { groupItems, levelText } from './skillLabels'

const GAP_STYLE: Record<GapStatus, { tone: string; icon: LucideIcon }> = {
  below: { tone: 'bg-red-50 text-red-900 ring-red-200', icon: ArrowDown },
  met: { tone: 'bg-emerald-50 text-emerald-900 ring-emerald-200', icon: Check },
  exceeds: { tone: 'bg-sky-50 text-sky-900 ring-sky-200', icon: ArrowUp },
  not_assessed: { tone: 'bg-white text-slate-600 ring-slate-300', icon: CircleDashed },
  requirement_pending: { tone: 'bg-slate-50 text-slate-600 ring-slate-200', icon: CircleHelp },
  scale_mismatch: { tone: 'bg-amber-50 text-amber-900 ring-amber-200', icon: TriangleAlert },
}

export function GapBadge({ status, steps }: { status: GapStatus; steps: number | null }) {
  const { t } = useTranslation()
  const { tone, icon: Icon } = GAP_STYLE[status]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset whitespace-nowrap ${tone}`}>
      <Icon aria-hidden="true" className="size-3" />
      {status === 'below' && steps ? t('skills.gap.belowBy', { count: steps }) : t(`skills.gap.${status}`)}
    </span>
  )
}

const RISK_TONE: Record<Risk, string> = {
  high: 'bg-red-50 text-red-900 ring-red-200',
  medium: 'bg-amber-50 text-amber-900 ring-amber-200',
  low: 'bg-emerald-50 text-emerald-900 ring-emerald-200',
}

export function RiskBadge({ risk }: { risk: Risk | null }) {
  const { t } = useTranslation()
  if (risk === null) return <span className="text-xs text-slate-500">{t('skills.risk.none')}</span>
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${RISK_TONE[risk]}`}>
      {t(`skills.risk.${risk}`)}
    </span>
  )
}

const RISK_EXPLAIN = {
  high: 'skills.risk.explainHigh',
  medium: 'skills.risk.explainMedium',
  low: 'skills.risk.explainLow',
} as const

/** Why the risk is what it is, using the server's figures (no recalculation here). */
export function RiskExplanation({ stats, margin }: { stats: ItemStats | undefined; margin: number }) {
  const { t } = useTranslation()
  if (!stats || stats.risk === null || stats.skilled === null || stats.required_headcount === null) return null
  return (
    <span className="mt-1 block text-[11px] text-slate-600">
      {t(RISK_EXPLAIN[stats.risk], { skilled: stats.skilled, required: stats.required_headcount, margin })}
    </span>
  )
}

function CellContent({ cell }: { cell: MatrixCell }) {
  const { t } = useTranslation()
  return (
    <span className="block space-y-1">
      <span className="block text-xs font-medium text-slate-900">
        {cell.assessed_level ? levelText(cell.assessed_level) : t('skills.notAssessedShort')}
      </span>
      <span className="block text-[11px] text-slate-500">
        {t('skills.requiredShort', { level: cell.required_level ? cell.required_level.code : t('skills.pendingShort') })}
      </span>
      <GapBadge status={cell.gap.status} steps={cell.gap.gap_steps} />
      {cell.needs_plan ? (
        <span className="flex items-center gap-1 text-[11px] font-medium text-ember-600">
          <ClipboardList aria-hidden="true" className="size-3" />
          {t('skills.needsPlan')}
        </span>
      ) : null}
    </span>
  )
}

/**
 * Required vs assessed levels. Desktop: employees × competencies table with a sticky
 * first column; phones: one card per employee. Text labels accompany every colour.
 */
export function MatrixGridView({
  grid,
  onCell,
}: {
  grid: MatrixGrid
  onCell?: (row: MatrixRow, item: MatrixItem, cell: MatrixCell) => void
}) {
  const { t } = useTranslation()
  const wide = useMediaQuery('(min-width: 768px)')
  const items = grid.matrix.items
  const groups = groupItems(items)
  const stats = new Map((grid.item_stats ?? []).map((s) => [s.competency_id, s]))
  const levels = grid.matrix.scale.levels

  if (items.length === 0) return <p className="text-sm text-slate-600">{t('skills.grid.noItems')}</p>
  if (grid.rows.length === 0 && !grid.item_stats) return <p className="text-sm text-slate-600">{t('skills.grid.noMembers')}</p>

  const cellButton = (row: MatrixRow, item: MatrixItem, cell: MatrixCell) =>
    onCell ? (
      <button
        type="button"
        onClick={() => onCell(row, item, cell)}
        aria-label={t('skills.grid.cellLabel', { employee: row.employee.name, competency: item.competency.name })}
        className="w-full rounded p-1 text-left hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
      >
        <CellContent cell={cell} />
      </button>
    ) : (
      <CellContent cell={cell} />
    )

  if (!wide) {
    return (
      <ul className="space-y-3">
        {grid.rows.map((row) => (
          <li key={row.employee.public_id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <p className="font-medium text-slate-900">
              {row.employee.name} <span className="text-xs text-slate-500">({row.employee.employee_code})</span>
            </p>
            <p className="mb-2 text-xs text-slate-600">{t('skills.grid.gaps', { count: row.gaps })}</p>
            <ul className="space-y-2">
              {items.map((item, index) => (
                <li key={item.competency.public_id} className="flex items-start justify-between gap-2 border-t border-slate-100 pt-2">
                  <span className="text-sm text-slate-800">{item.competency.name}</span>
                  <span className="shrink-0">{cellButton(row, item, row.cells[index])}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full border-separate border-spacing-0 text-sm">
        <caption className="sr-only">{t('skills.grid.caption', { name: grid.matrix.name })}</caption>
        <thead className="bg-slate-50">
          {groups.some((g) => g.label) ? (
            <tr>
              <th scope="col" className="sticky left-0 z-10 bg-slate-50" />
              {groups.map((group, index) => (
                <th
                  key={`${group.label ?? 'none'}-${index}`}
                  scope="colgroup"
                  colSpan={group.items.length}
                  className="border-b border-l border-slate-200 px-2 py-1 text-left text-xs font-semibold text-slate-700"
                >
                  {group.label ?? ''}
                </th>
              ))}
            </tr>
          ) : null}
          <tr>
            <th scope="col" className={`${thClassName} sticky left-0 z-10 min-w-48 border-b border-slate-200 bg-slate-50`}>
              {t('skills.grid.employee')}
            </th>
            {items.map((item) => (
              <th key={item.competency.public_id} scope="col" className={`${thClassName} min-w-36 border-b border-l border-slate-200 normal-case`}>
                <span className="block font-semibold text-slate-800">{item.competency.name}</span>
                <span className="block text-[11px] font-normal text-slate-500">
                  {t('skills.requiredShort', { level: item.required_level ? levelText(item.required_level) : t('skills.pendingShort') })}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row) => (
            <tr key={row.employee.public_id}>
              <th scope="row" className={`${tdClassName} sticky left-0 z-10 border-b border-slate-100 bg-white text-left font-medium`}>
                {row.employee.name}
                <span className="block text-xs font-normal text-slate-500">
                  {row.employee.employee_code} · {t('skills.grid.gaps', { count: row.gaps })}
                </span>
              </th>
              {row.cells.map((cell, index) => (
                <td key={cell.competency_id} className="border-b border-l border-slate-100 p-1 align-top">
                  {cellButton(row, items[index], cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {grid.item_stats ? (
          <tfoot className="bg-slate-50 text-xs">
            {levels.map((level) => (
              <tr key={level.public_id}>
                <th scope="row" className="sticky left-0 z-10 border-t border-slate-200 bg-slate-50 px-3 py-1 text-left font-medium text-slate-700">
                  {t('skills.stats.atLevel', { level: levelText(level) })}
                </th>
                {items.map((item) => (
                  <td key={item.competency.public_id} className="border-t border-l border-slate-200 px-2 py-1 tabular-nums">
                    {stats.get(item.competency.public_id)?.counts_by_rank[String(level.rank)] ?? 0}
                  </td>
                ))}
              </tr>
            ))}
            {(
              [
                ['notAssessed', (id: string) => stats.get(id)?.not_assessed ?? 0],
                ['skilled', (id: string) => stats.get(id)?.skilled ?? '—'],
                ['required', (id: string) => stats.get(id)?.required_headcount ?? '—'],
              ] as const
            ).map(([key, value]) => (
              <tr key={key}>
                <th scope="row" className="sticky left-0 z-10 border-t border-slate-200 bg-slate-50 px-3 py-1 text-left font-medium text-slate-700">
                  {t(`skills.stats.${key}`)}
                </th>
                {items.map((item) => (
                  <td key={item.competency.public_id} className="border-t border-l border-slate-200 px-2 py-1 tabular-nums">
                    {value(item.competency.public_id)}
                  </td>
                ))}
              </tr>
            ))}
            <tr>
              <th scope="row" className="sticky left-0 z-10 border-t border-slate-200 bg-slate-50 px-3 py-1 text-left font-medium text-slate-700">
                {t('skills.stats.risk')}
              </th>
              {items.map((item) => (
                <td key={item.competency.public_id} className="border-t border-l border-slate-200 px-2 py-1">
                  <RiskBadge risk={stats.get(item.competency.public_id)?.risk ?? null} />
                  <RiskExplanation stats={stats.get(item.competency.public_id)} margin={grid.matrix.risk_medium_margin} />
                </td>
              ))}
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  )
}

/** Summary chips (counts per gap status, risk and plan flags). */
export function SummaryChips({ summary }: { summary: Record<string, number> }) {
  const { t } = useTranslation()
  const keys = [
    'below',
    'met',
    'exceeds',
    'not_assessed',
    'requirement_pending',
    'needs_plan',
    'risk_high',
    'risk_medium',
    'risk_low',
  ] as const
  return (
    <ul className="flex flex-wrap gap-2" aria-label={t('skills.summary.label')}>
      {keys
        .filter((key) => summary[key] !== undefined)
        .map((key) => (
          <li key={key} className="rounded-full bg-white px-3 py-1 text-xs text-slate-700 shadow-sm ring-1 ring-slate-200">
            {t(`skills.summary.${key}`)}: <span className="font-semibold text-slate-900">{summary[key]}</span>
          </li>
        ))}
    </ul>
  )
}

export function Legend({ levels }: { levels: Level[] }) {
  const { t } = useTranslation()
  return (
    <details className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <summary className="cursor-pointer font-medium text-slate-800">{t('skills.legend')}</summary>
      <dl className="mt-2 grid gap-1 sm:grid-cols-2">
        {levels.map((level) => (
          <Fragment key={level.public_id}>
            <dt className="font-medium text-slate-900">
              {level.code} · {level.label}
            </dt>
            <dd className="text-slate-600">{level.description ?? '—'}</dd>
          </Fragment>
        ))}
      </dl>
    </details>
  )
}
