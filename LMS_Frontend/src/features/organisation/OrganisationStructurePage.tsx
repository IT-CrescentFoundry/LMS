import { ArrowLeft, ChevronsDownUp, ChevronsUpDown, Plus } from 'lucide-react'
import { useCallback, useId, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { useMediaQuery, WIDE_LAYOUT_QUERY } from '../../hooks/useMediaQuery'
import { formatDate } from '../../lib/format'
import type { OrgUnit } from '../../types/organisation'
import { AdminErrorState } from '../admin/AdminParts'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { MobileUnitBrowser } from './MobileUnitBrowser'
import { localName } from './names'
import { NoticeBanner, OrgPageHeader, type SuccessNotice } from './OrgParts'
import { useOrgTree, useUnitTypes } from './orgQueries'
import { OrgTree } from './OrgTree'
import {
  ancestorIds,
  buildTreeIndex,
  isFilterActive,
  matchingIds,
  STATUS_VIEWS,
  visibleRows,
  withAncestors,
  type StatusView,
} from './tree'
import {
  CloseUnitDialog,
  MoveUnitDialog,
  ReopenUnitDialog,
  UnitFormDialog,
  type UnitDialogState,
} from './UnitDialogs'
import { UnitDetailsPanel } from './UnitDetailsPanel'

/**
 * Organisation Builder (`/organisation`). The structure is shown as of a date;
 * changes go through the audited backend services. Units are never deleted:
 * they are moved, corrected, closed or reopened.
 */
export function OrganisationStructurePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManage = useHasPermission(PERMISSIONS.ORGANISATION_MANAGE)
  const wide = useMediaQuery(WIDE_LAYOUT_QUERY)
  const ids = { search: useId(), type: useId(), status: useId(), asOf: useId() }

  const [search, setSearch] = useState('')
  const [unitTypeId, setUnitTypeId] = useState('')
  const [statusView, setStatusView] = useState<StatusView>('active')
  const [asOf, setAsOf] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set())
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(new Set())
  const [mobileParent, setMobileParent] = useState<string | null>(null)
  const [mobileDetails, setMobileDetails] = useState(false)
  const [dialog, setDialog] = useState<UnitDialogState | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)

  const treeQuery = useOrgTree({ as_of: asOf || undefined, include_closed: statusView !== 'active' })
  const unitTypesQuery = useUnitTypes()
  useRefreshSessionOnForbidden(treeQuery.error)

  const index = useMemo(
    () => (treeQuery.data ? buildTreeIndex(treeQuery.data.nodes, language) : null),
    [treeQuery.data, language],
  )
  const filter = { query: search, unitTypeId, statusView }
  const filterActive = isFilterActive(filter)
  const matches = useMemo(
    () => (index ? matchingIds(index, { query: search, unitTypeId, statusView }, language) : null),
    [index, search, unitTypeId, statusView, language],
  )
  const visible = useMemo(() => (index && matches ? withAncestors(index, matches) : null), [index, matches])
  const effectiveExpanded = useMemo(() => {
    if (!visible) return expanded
    const result = new Set([...visible].filter((id) => !collapsed.has(id)))
    for (const id of expanded) result.add(id)
    return result
  }, [visible, expanded, collapsed])
  const rows = useMemo(
    () => (index ? visibleRows(index, effectiveExpanded, visible) : []),
    [index, effectiveExpanded, visible],
  )

  const typeNames = useMemo(
    () => new Map((unitTypesQuery.data ?? []).map((type) => [type.public_id, localName(type, language)])),
    [unitTypesQuery.data, language],
  )
  const typeName = useCallback(
    (typeId: string, fallback: string) => typeNames.get(typeId) ?? fallback,
    [typeNames],
  )

  function toggle(id: string, expand: boolean) {
    setExpanded((current) => {
      const next = new Set(current)
      if (expand) next.add(id)
      else next.delete(id)
      return next
    })
    setCollapsed((current) => {
      const next = new Set(current)
      if (expand) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function expandAll() {
    if (!index) return
    setCollapsed(new Set())
    setExpanded(new Set([...index.children.keys()].filter((key): key is string => key !== null)))
  }

  function collapseAll() {
    setExpanded(new Set())
    setCollapsed(new Set(index ? [...index.byId.keys()] : []))
  }

  function select(id: string) {
    setSelectedId(id)
    setMobileDetails(true)
  }

  function onDone(result: SuccessNotice, unit: OrgUnit) {
    setDialog(null)
    setNotice(result)
    setSelectedId(unit.public_id)
    setFocusedId(unit.public_id)
    if (index) {
      const path = unit.path.map((ref) => ref.public_id)
      setExpanded((current) => new Set([...current, ...path, ...ancestorIds(index, unit.public_id)]))
    }
  }

  const viewedDate = treeQuery.data?.as_of
  const matchCount = matches?.size ?? 0

  const details = selectedId ? (
    <UnitDetailsPanel
      key={selectedId}
      unitId={selectedId}
      asOf={viewedDate}
      index={index}
      canManage={canManage}
      onSelect={select}
      onAction={setDialog}
      typeName={typeName}
    />
  ) : (
    <p className="text-sm text-slate-600">{t('org.structure.details.selectPrompt')}</p>
  )

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.structure.title')}
        subtitle={t('org.structure.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setDialog({ kind: 'create', parent: null })} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.actions.addTopLevel')}
          </button>
        }
      />

      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}

      <div
        role="search"
        aria-label={t('org.structure.filters')}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-4"
      >
        <div className="space-y-1.5">
          <label htmlFor={ids.search} className={labelClassName}>
            {t('org.structure.search')}
          </label>
          <input
            id={ids.search}
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            maxLength={100}
            placeholder={t('org.structure.searchPlaceholder')}
            autoComplete="off"
            className={inputClassName()}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.type} className={labelClassName}>
            {t('org.fields.unitType')}
          </label>
          <select id={ids.type} value={unitTypeId} onChange={(event) => setUnitTypeId(event.target.value)} className={inputClassName()}>
            <option value="">{t('org.structure.allTypes')}</option>
            {(unitTypesQuery.data ?? []).map((type) => (
              <option key={type.public_id} value={type.public_id}>
                {localName(type, language)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.status} className={labelClassName}>
            {t('org.structure.statusView')}
          </label>
          <select
            id={ids.status}
            value={statusView}
            onChange={(event) => setStatusView(event.target.value as StatusView)}
            className={inputClassName()}
          >
            {STATUS_VIEWS.map((view) => (
              <option key={view} value={view}>
                {t(`org.structure.statusViews.${view}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.asOf} className={labelClassName}>
            {t('org.structure.asOf')}
          </label>
          <div className="flex gap-2">
            <input
              id={ids.asOf}
              type="date"
              value={asOf}
              onChange={(event) => setAsOf(event.target.value)}
              aria-describedby={`${ids.asOf}-hint`}
              className={inputClassName()}
            />
            {asOf ? (
              <button type="button" onClick={() => setAsOf('')} className={secondaryButtonClassName}>
                {t('org.structure.today')}
              </button>
            ) : null}
          </div>
          <p id={`${ids.asOf}-hint`} className="text-xs text-slate-600">
            {t('org.structure.asOfHint')}
          </p>
        </div>
      </div>

      {treeQuery.isPending ? (
        <LoadingState />
      ) : treeQuery.isError || !index ? (
        <AdminErrorState
          title={t('org.structure.loadError')}
          error={treeQuery.error}
          onRetry={() => void treeQuery.refetch()}
          isRetrying={treeQuery.isFetching}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          {wide || !mobileDetails || selectedId === null ? (
            <section aria-labelledby="org-tree-heading" className="min-w-0 rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
                <div className="min-w-0">
                  <h2 id="org-tree-heading" className="font-semibold text-slate-900">
                    {t('org.structure.tree.label')}
                  </h2>
                  <p role="status" aria-live="polite" className="text-xs text-slate-600">
                    {viewedDate ? t('org.structure.viewingAsOf', { date: formatDate(viewedDate, language) }) : null}
                    {filterActive ? ` · ${t('org.structure.matches', { count: matchCount })}` : null}
                  </p>
                </div>
                {wide ? (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={expandAll}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    >
                      <ChevronsUpDown aria-hidden="true" className="size-3.5" />
                      {t('org.actions.expandAll')}
                    </button>
                    <button
                      type="button"
                      onClick={collapseAll}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    >
                      <ChevronsDownUp aria-hidden="true" className="size-3.5" />
                      {t('org.actions.collapseAll')}
                    </button>
                  </div>
                ) : null}
              </div>
              {index.byId.size === 0 ? (
                <p className="p-4 text-sm text-slate-600">{t('org.structure.empty')}</p>
              ) : filterActive && matchCount === 0 ? (
                <p className="p-4 text-sm text-slate-600">{t('org.structure.noMatches')}</p>
              ) : wide ? (
                <div className="p-2">
                  <OrgTree
                    label={t('org.structure.tree.label')}
                    rows={rows}
                    selectedId={selectedId}
                    focusedId={focusedId}
                    onFocusChange={setFocusedId}
                    onSelect={select}
                    onToggle={toggle}
                    matches={matches}
                    typeName={typeName}
                  />
                </div>
              ) : (
                <MobileUnitBrowser
                  index={index}
                  visible={visible}
                  matches={matches}
                  parentId={mobileParent}
                  onParentChange={setMobileParent}
                  onSelect={select}
                  typeName={typeName}
                />
              )}
            </section>
          ) : null}

          {wide ? (
            <section aria-label={t('org.structure.details.region')} className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              {details}
            </section>
          ) : selectedId !== null && mobileDetails ? (
            <section aria-label={t('org.structure.details.region')} className="min-w-0 space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <button type="button" onClick={() => setMobileDetails(false)} className={secondaryButtonClassName}>
                <ArrowLeft aria-hidden="true" className="size-4" />
                {t('org.structure.drill.backToList')}
              </button>
              {details}
            </section>
          ) : null}
        </div>
      )}

      {dialog?.kind === 'create' ? (
        <UnitFormDialog mode="create" parent={dialog.parent} onClose={() => setDialog(null)} onDone={onDone} />
      ) : null}
      {dialog?.kind === 'correct' ? (
        <UnitFormDialog mode="correct" unit={dialog.unit} onClose={() => setDialog(null)} onDone={onDone} />
      ) : null}
      {dialog?.kind === 'move' && index ? (
        <MoveUnitDialog unit={dialog.unit} index={index} onClose={() => setDialog(null)} onDone={onDone} />
      ) : null}
      {dialog?.kind === 'close' ? (
        <CloseUnitDialog unit={dialog.unit} onClose={() => setDialog(null)} onDone={onDone} />
      ) : null}
      {dialog?.kind === 'reopen' ? (
        <ReopenUnitDialog unit={dialog.unit} onClose={() => setDialog(null)} onDone={onDone} />
      ) : null}
    </div>
  )
}
