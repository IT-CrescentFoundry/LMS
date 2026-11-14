import { ArrowRightLeft, CircleOff, PencilLine, Plus, RotateCcw } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '../../components/LoadingState'
import { SUPPORTED_LANGUAGES } from '../../i18n/languages'
import { formatDate } from '../../lib/format'
import { TRANSLATION_LOCALES, type OrgUnit } from '../../types/organisation'
import { AdminErrorState } from '../admin/AdminParts'
import { localName } from './names'
import { RowButton, UnitStatusBadge } from './OrgParts'
import { useOrgUnit, useUnitHistory } from './orgQueries'
import type { TreeIndex } from './tree'
import type { UnitDialogState } from './UnitDialogs'

interface UnitDetailsPanelProps {
  unitId: string
  asOf: string | undefined
  index: TreeIndex | null
  canManage: boolean
  onSelect: (id: string) => void
  onAction: (dialog: UnitDialogState) => void
  typeName: (typeId: string, fallback: string) => string
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="text-sm break-words text-slate-900">{children}</dd>
    </div>
  )
}

/** Details of one unit as of the viewed date, with its children and placement history. */
export function UnitDetailsPanel({
  unitId,
  asOf,
  index,
  canManage,
  onSelect,
  onAction,
  typeName,
}: UnitDetailsPanelProps) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const unitQuery = useOrgUnit(unitId, asOf)
  const historyQuery = useUnitHistory(unitId)

  if (unitQuery.isPending) return <LoadingState />
  if (unitQuery.isError) {
    return (
      <AdminErrorState
        title={t('org.structure.details.loadError')}
        error={unitQuery.error}
        onRetry={() => void unitQuery.refetch()}
        isRetrying={unitQuery.isFetching}
      />
    )
  }

  const unit: OrgUnit = unitQuery.data
  const displayName = localName(unit, language)
  const children = index?.children.get(unit.public_id) ?? []
  const isClosed = unit.effective_to !== null
  const notRecorded = t('org.common.notRecorded')
  const translations = TRANSLATION_LOCALES.filter((locale) => unit.translations[locale])

  return (
    <article aria-labelledby="unit-details-title" className="space-y-5">
      <header className="space-y-2">
        {unit.path.length > 0 ? (
          <p className="text-xs break-words text-slate-500">
            <span className="sr-only">{t('org.structure.details.path')}: </span>
            {unit.path.map((ref) => localName(ref, language)).join(' › ')}
          </p>
        ) : null}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 id="unit-details-title" className="text-xl font-semibold break-words text-slate-900">
              {displayName}
            </h2>
            {displayName !== unit.name ? (
              <p className="text-sm text-slate-600">
                {t('org.structure.details.recordedName')}: {unit.name}
              </p>
            ) : null}
          </div>
          <UnitStatusBadge status={unit.status} />
        </div>
      </header>

      {canManage ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label={t('org.structure.details.actions')}>
          {!isClosed ? (
            <RowButton onClick={() => onAction({ kind: 'create', parent: unit })}>
              <Plus aria-hidden="true" className="size-4" />
              {t('org.actions.addChild')}
            </RowButton>
          ) : null}
          <RowButton onClick={() => onAction({ kind: 'correct', unit })}>
            <PencilLine aria-hidden="true" className="size-4" />
            {t('org.actions.correct')}
          </RowButton>
          {!isClosed ? (
            <>
              <RowButton onClick={() => onAction({ kind: 'move', unit })}>
                <ArrowRightLeft aria-hidden="true" className="size-4" />
                {t('org.actions.move')}
              </RowButton>
              <RowButton onClick={() => onAction({ kind: 'close', unit })}>
                <CircleOff aria-hidden="true" className="size-4" />
                {t('org.actions.closeUnit')}
              </RowButton>
            </>
          ) : (
            <RowButton onClick={() => onAction({ kind: 'reopen', unit })}>
              <RotateCcw aria-hidden="true" className="size-4" />
              {t('org.actions.reopen')}
            </RowButton>
          )}
        </div>
      ) : null}

      <dl className="grid gap-3 sm:grid-cols-2">
        <Detail label={t('org.fields.code')}>
          <span className="font-mono">{unit.code}</span>
        </Detail>
        <Detail label={t('org.fields.unitType')}>{typeName(unit.unit_type.public_id, unit.unit_type.name)}</Detail>
        <Detail label={t('org.fields.parent')}>
          {unit.parent ? localName(unit.parent, language) : t('org.common.topLevel')}
        </Detail>
        <Detail label={t('org.fields.location')}>{unit.location ? unit.location.name : t('org.common.none')}</Detail>
        <Detail label={t('org.fields.effectiveFrom')}>
          {unit.effective_from ? formatDate(unit.effective_from, language) : notRecorded}
        </Detail>
        <Detail label={t('org.fields.closedFrom')}>
          {unit.effective_to ? formatDate(unit.effective_to, language) : t('org.common.open')}
        </Detail>
        <Detail label={t('org.fields.shortName')}>{unit.short_name ?? t('org.common.none')}</Detail>
        <Detail label={t('org.fields.externalRef')}>{unit.external_ref ?? t('org.common.none')}</Detail>
      </dl>

      {translations.length > 0 ? (
        <section aria-labelledby="unit-translations" className="space-y-1">
          <h3 id="unit-translations" className="text-sm font-semibold text-slate-900">
            {t('org.fields.translations')}
          </h3>
          <ul className="space-y-0.5 text-sm text-slate-800">
            {translations.map((locale) => (
              <li key={locale} lang={locale}>
                <span className="text-slate-500">
                  {SUPPORTED_LANGUAGES.find((item) => item.code === locale)?.nativeName}:{' '}
                </span>
                {unit.translations[locale]}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="unit-children" className="space-y-2">
        <h3 id="unit-children" className="text-sm font-semibold text-slate-900">
          {t('org.structure.details.children', { count: children.length })}
        </h3>
        {children.length === 0 ? (
          <p className="text-sm text-slate-600">{t('org.structure.details.noChildren')}</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
            {children.map((child) => (
              <li key={child.public_id}>
                <button
                  type="button"
                  onClick={() => onSelect(child.public_id)}
                  className="flex w-full flex-wrap items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                >
                  <span className="min-w-0 break-words">
                    <span className="font-medium text-slate-900">{localName(child, language)}</span>{' '}
                    <span className="text-xs text-slate-500">
                      {child.code} · {typeName(child.unit_type.public_id, child.unit_type.name)}
                    </span>
                  </span>
                  {child.status !== 'active' ? <UnitStatusBadge status={child.status} /> : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="unit-history" className="space-y-2">
        <h3 id="unit-history" className="text-sm font-semibold text-slate-900">
          {t('org.structure.details.history')}
        </h3>
        {historyQuery.isPending ? (
          <LoadingState />
        ) : historyQuery.isError ? (
          <AdminErrorState
            title={t('org.structure.details.historyError')}
            error={historyQuery.error}
            onRetry={() => void historyQuery.refetch()}
            isRetrying={historyQuery.isFetching}
          />
        ) : historyQuery.data.placements.length === 0 ? (
          <p className="text-sm text-slate-600">{t('org.structure.details.alwaysTopLevel')}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg ring-1 ring-slate-200">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('org.structure.details.historyCaption', { name: displayName })}</caption>
              <thead className="bg-slate-50 text-xs text-slate-600">
                <tr>
                  <th scope="col" className="px-3 py-2 font-semibold">
                    {t('org.fields.parent')}
                  </th>
                  <th scope="col" className="px-3 py-2 font-semibold">
                    {t('org.fields.from')}
                  </th>
                  <th scope="col" className="px-3 py-2 font-semibold">
                    {t('org.fields.to')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historyQuery.data.placements.map((placement, position) => (
                  <tr key={`${placement.parent.public_id}-${placement.effective_from ?? 'start'}-${position}`}>
                    <td className="px-3 py-2 break-words text-slate-900">
                      {localName(placement.parent, language)}{' '}
                      <span className="font-mono text-xs text-slate-500">{placement.parent.code}</span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-slate-700">
                      {placement.effective_from ? formatDate(placement.effective_from, language) : notRecorded}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-slate-700">
                      {placement.effective_to ? formatDate(placement.effective_to, language) : t('org.common.current')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-xs text-slate-500">{t('org.structure.details.historyNote')}</p>
      </section>
    </article>
  )
}
