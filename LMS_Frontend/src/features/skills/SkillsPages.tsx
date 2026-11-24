import { ChevronRight, ListChecks, Pencil, Plus, Users } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'

import { cardClassName, EmptyState, FeatureError, PageHeader } from '../../components/FeatureState'
import { apiErrorCode } from '../../lib/featureErrors'
import { inputClassName, labelClassName, primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { LocationSelect, UnitSelect } from '../../components/Pickers'
import type { MatrixCell, MatrixItem, MatrixRow } from '../../types/competency'
import { useAuth, useHasPermission } from '../auth/authContext'
import { hasAnyPermission, PERMISSIONS } from '../auth/permissions'
import { useGrid, useMatrices, useMySkills } from './competencyQueries'
import { AssessmentPanel, MatrixFormDialog, MatrixItemsDialog, MembersDialog } from './MatrixDialogs'
import { Legend, MatrixGridView, SummaryChips } from './SkillParts'

/** Users who may browse matrices see the list; employees with own access see their skills. */
export function SkillsHomePage() {
  const { user } = useAuth()
  const browse = hasAnyPermission(user, [
    PERMISSIONS.COMPETENCY_VIEW,
    PERMISSIONS.COMPETENCY_MANAGE,
    PERMISSIONS.TEAM_LEARNING_VIEW,
  ])
  return browse ? <MatrixListPage /> : <MySkillsPage />
}

export function MatrixListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const canManage = useHasPermission(PERMISSIONS.COMPETENCY_MANAGE)
  const ownView = useHasPermission(PERMISSIONS.LEARNING_OWN_VIEW)
  const [q, setQ] = useState('')
  const [unit, setUnit] = useState('')
  const [location, setLocation] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [creating, setCreating] = useState(false)
  const matrices = useMatrices({
    q: q.trim() || undefined,
    unit: unit || undefined,
    location: location || undefined,
    include_inactive: includeInactive,
  })
  const ids = { q: useId(), inactive: useId() }
  return (
    <div className="space-y-6">
      <PageHeader
        title={t('skills.list.title')}
        description={t('skills.list.description')}
        actions={
          <>
            {ownView ? (
              <Link to="/skills/me" className={secondaryButtonClassName}>
                {t('skills.my.link')}
              </Link>
            ) : null}
            {canManage ? (
              <button type="button" onClick={() => setCreating(true)} className={primaryButtonClassName}>
                <Plus aria-hidden="true" className="size-4" />
                {t('skills.matrix.create')}
              </button>
            ) : null}
          </>
        }
      />
      <div className={`${cardClassName} grid gap-4 sm:grid-cols-2 lg:grid-cols-4`}>
        <div className="space-y-1.5">
          <label htmlFor={ids.q} className={labelClassName}>
            {t('skills.list.search')}
          </label>
          <input id={ids.q} type="search" value={q} onChange={(e) => setQ(e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <UnitSelect label={t('skills.fields.unit')} value={unit} onChange={setUnit} />
        <LocationSelect label={t('skills.fields.location')} value={location} onChange={setLocation} />
        <label htmlFor={ids.inactive} className="flex items-center gap-2 text-sm">
          <input id={ids.inactive} type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="size-4 accent-brand-700" />
          {t('skills.list.showInactive')}
        </label>
      </div>
      {matrices.isPending ? (
        <LoadingState />
      ) : matrices.isError ? (
        <FeatureError error={matrices.error} title={t('skills.list.loadError')} onRetry={() => void matrices.refetch()} />
      ) : matrices.data.length === 0 ? (
        <EmptyState title={t('skills.list.empty')} body={canManage ? t('skills.list.emptyManage') : undefined} />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {matrices.data.map((matrix) => (
            <li key={matrix.public_id} className={`${cardClassName} space-y-2`}>
              <Link to={`/skills/${matrix.public_id}`} className="text-lg font-semibold text-brand-700 hover:underline">
                {matrix.name}
              </Link>
              <p className="text-xs text-slate-500">
                {matrix.code} · {matrix.scale.name}
                {matrix.is_active ? '' : ` · ${t('skills.list.inactive')}`}
              </p>
              <p className="text-sm text-slate-700">
                {[matrix.org_unit?.name, matrix.location?.name, matrix.designation?.name, matrix.functional_role?.name]
                  .filter(Boolean)
                  .join(' · ') || t('skills.list.noScope')}
              </p>
              <p className="flex gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1">
                  <ListChecks aria-hidden="true" className="size-4" />
                  {t('skills.list.items', { count: matrix.items.length })}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Users aria-hidden="true" className="size-4" />
                  {t('skills.list.members', { count: matrix.member_count })}
                </span>
              </p>
            </li>
          ))}
        </ul>
      )}
      {creating ? (
        <MatrixFormDialog matrix={null} onClose={() => setCreating(false)} onSaved={(m) => navigate(`/skills/${m.public_id}`)} />
      ) : null}
    </div>
  )
}

type Selected = { row: MatrixRow; item: MatrixItem; cell: MatrixCell }

export function MatrixPage() {
  const { t } = useTranslation()
  const { matrixId = '' } = useParams()
  const grid = useGrid(matrixId)
  const canManage = useHasPermission(PERMISSIONS.COMPETENCY_MANAGE)
  const [dialog, setDialog] = useState<'edit' | 'items' | 'members' | null>(null)
  const [selected, setSelected] = useState<Selected | null>(null)
  if (grid.isPending) return <LoadingState />
  if (grid.isError) return <FeatureError error={grid.error} title={t('skills.grid.loadError')} onRetry={() => void grid.refetch()} />
  const { matrix } = grid.data
  return (
    <div className="space-y-5">
      <nav aria-label={t('org.breadcrumb')}>
        <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-600">
          <li>
            <Link to="/skills" className="hover:text-brand-700 hover:underline">
              {t('nav.skillMatrix')}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-4 text-slate-400" />
          </li>
          <li aria-current="page" className="font-medium text-slate-900">
            {matrix.code}
          </li>
        </ol>
      </nav>
      <PageHeader
        title={matrix.name}
        description={[matrix.description, matrix.org_unit?.name, matrix.location?.name, matrix.scale.name].filter(Boolean).join(' · ')}
        actions={
          canManage ? (
            <>
              <button type="button" onClick={() => setDialog('edit')} className={secondaryButtonClassName}>
                <Pencil aria-hidden="true" className="size-4" />
                {t('skills.matrix.edit')}
              </button>
              <button type="button" onClick={() => setDialog('items')} className={secondaryButtonClassName}>
                <ListChecks aria-hidden="true" className="size-4" />
                {t('skills.items.button')}
              </button>
              <button type="button" onClick={() => setDialog('members')} className={secondaryButtonClassName}>
                <Users aria-hidden="true" className="size-4" />
                {t('skills.members.button')}
              </button>
            </>
          ) : null
        }
      />
      <p className="text-xs text-slate-600">{t(`training.scope.${grid.data.scope}`)}</p>
      <SummaryChips summary={grid.data.summary} />
      <Legend levels={matrix.scale.levels} />
      <MatrixGridView grid={grid.data} onCell={(row, item, cell) => setSelected({ row, item, cell })} />
      {grid.data.item_stats ? <p className="text-xs text-slate-500">{t('skills.stats.note', { margin: matrix.risk_medium_margin })}</p> : null}
      {dialog === 'edit' ? <MatrixFormDialog matrix={matrix} onClose={() => setDialog(null)} /> : null}
      {dialog === 'items' ? <MatrixItemsDialog matrix={matrix} onClose={() => setDialog(null)} /> : null}
      {dialog === 'members' ? (
        <MembersDialog matrix={matrix} members={grid.data.rows.map((r) => r.employee)} onClose={() => setDialog(null)} />
      ) : null}
      {selected ? (
        <AssessmentPanel matrix={matrix} row={selected.row} item={selected.item} cell={selected.cell} onClose={() => setSelected(null)} />
      ) : null}
    </div>
  )
}

export function MySkillsPage() {
  const { t } = useTranslation()
  const skills = useMySkills()
  return (
    <div className="space-y-6">
      <PageHeader title={t('skills.my.title')} description={t('skills.my.description')} />
      {skills.isPending ? (
        <LoadingState />
      ) : skills.isError && apiErrorCode(skills.error) === 'employee_not_linked' ? (
        <EmptyState title={t('skills.my.notLinked')} />
      ) : skills.isError ? (
        <FeatureError error={skills.error} title={t('skills.my.loadError')} onRetry={() => void skills.refetch()} />
      ) : skills.data.matrices.length === 0 ? (
        <EmptyState title={t('skills.my.empty')} />
      ) : (
        skills.data.matrices.map((grid) => (
          <section key={grid.matrix.public_id} aria-label={grid.matrix.name} className="space-y-3">
            <h2 className="text-lg font-semibold text-slate-900">{grid.matrix.name}</h2>
            <SummaryChips summary={grid.summary} />
            <MatrixGridView grid={grid} />
          </section>
        ))
      )}
    </div>
  )
}
