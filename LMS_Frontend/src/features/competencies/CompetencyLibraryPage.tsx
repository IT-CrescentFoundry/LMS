import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import {
  cardClassName,
  EmptyState,
  FeatureError,
  Field,
  PageHeader,
  TabBar,
  tableClassName,
  tableWrapClassName,
  tdClassName,
  thClassName,
} from '../../components/FeatureState'
import { inputClassName, labelClassName, primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { competencyService, COMPETENCY_PAGE_SIZE } from '../../services/competencyService'
import { COMPETENCY_STATUSES, type Body, type Competency, type CompetencyStatus, type LevelInput, type Scale } from '../../types/competency'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { useCategories, useCompetencies, useCompetencyMutation, useScales } from '../skills/competencyQueries'
import { formatDateTime } from '../../lib/format'
import { levelText } from '../skills/skillLabels'
import { DialogActions, DialogError, FormField } from '../training/EventDialogs'
import { Pager } from '../training/TrainingRegisterPage'

type Tab = 'library' | 'scales'
const text = (value: string): string | null => (value.trim() === '' ? null : value.trim())

/** Competency library and proficiency scales. */
export function CompetencyLibraryPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('library')
  return (
    <div className="space-y-6">
      <PageHeader title={t('comp.title')} description={t('comp.description')} />
      <TabBar<Tab>
        label={t('comp.tabs.label')}
        value={tab}
        onChange={setTab}
        tabs={[
          { value: 'library', label: t('comp.tabs.library') },
          { value: 'scales', label: t('comp.tabs.scales') },
        ]}
      />
      {tab === 'library' ? <LibraryTab /> : <ScalesTab />}
    </div>
  )
}

function LibraryTab() {
  const { t, i18n } = useTranslation()
  const canManage = useHasPermission(PERMISSIONS.COMPETENCY_MANAGE)
  const [draftQ, setDraftQ] = useState('')
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [status, setStatus] = useState<CompetencyStatus | ''>('')
  const [offset, setOffset] = useState(0)
  const list = useCompetencies(
    { q: q || undefined, category: category || undefined, include_inactive: includeInactive, status: status || undefined },
    offset,
  )
  const categories = useCategories()
  const [selected, setSelected] = useState<Competency | null>(null)
  const [editing, setEditing] = useState<Competency | 'new' | null>(null)
  const ids = { q: useId(), category: useId(), inactive: useId(), status: useId() }
  function submit(e: FormEvent) {
    e.preventDefault()
    setOffset(0)
    setQ(draftQ.trim())
  }
  return (
    <div className="space-y-4">
      <form role="search" aria-label={t('comp.filters')} onSubmit={submit} className={`${cardClassName} flex flex-wrap items-end gap-4`}>
        <div className="min-w-0 flex-1 space-y-1.5 sm:min-w-56">
          <label htmlFor={ids.q} className={labelClassName}>
            {t('comp.search')}
          </label>
          <input id={ids.q} type="search" value={draftQ} onChange={(e) => setDraftQ(e.target.value)} maxLength={100} className={inputClassName()} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.category} className={labelClassName}>
            {t('comp.fields.category')}
          </label>
          <select
            id={ids.category}
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setOffset(0)
            }}
            className={inputClassName()}
          >
            <option value="">{t('training.register.any')}</option>
            {(categories.data ?? []).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor={ids.status} className={labelClassName}>
            {t('comp.governance.label')}
          </label>
          <select
            id={ids.status}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as CompetencyStatus | '')
              setOffset(0)
            }}
            className={inputClassName()}
          >
            <option value="">{t('training.register.any')}</option>
            {COMPETENCY_STATUSES.map((value) => (
              <option key={value} value={value}>
                {t(`comp.governance.${value}`)}
              </option>
            ))}
          </select>
        </div>
        <label htmlFor={ids.inactive} className="flex items-center gap-2 pb-2.5 text-sm">
          <input id={ids.inactive} type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="size-4 accent-brand-700" />
          {t('comp.showInactive')}
        </label>
        <button type="submit" className={primaryButtonClassName}>
          {t('training.register.apply')}
        </button>
        {canManage ? (
          <button type="button" onClick={() => setEditing('new')} className={secondaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('comp.create')}
          </button>
        ) : null}
      </form>
      {list.isPending ? (
        <LoadingState />
      ) : list.isError ? (
        <FeatureError error={list.error} title={t('comp.loadError')} onRetry={() => void list.refetch()} />
      ) : list.data.items.length === 0 ? (
        <EmptyState title={t('comp.empty')} body={t('comp.emptyBody')} />
      ) : (
        <>
          <div className={tableWrapClassName}>
            <table className={tableClassName}>
              <caption className="sr-only">{t('comp.caption')}</caption>
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className={thClassName}>{t('comp.fields.code')}</th>
                  <th scope="col" className={thClassName}>{t('comp.fields.name')}</th>
                  <th scope="col" className={thClassName}>{t('comp.fields.category')}</th>
                  <th scope="col" className={thClassName}>{t('comp.fields.scale')}</th>
                  <th scope="col" className={thClassName}>{t('comp.fields.status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {list.data.items.map((c) => (
                  <tr key={c.public_id}>
                    <td className={`${tdClassName} font-mono text-xs`}>{c.code}</td>
                    <td className={tdClassName}>
                      <button type="button" onClick={() => setSelected(c)} className="text-left font-medium text-brand-700 hover:underline">
                        {c.name}
                      </button>
                    </td>
                    <td className={tdClassName}>
                      {c.category ?? '—'}
                      {c.sub_category ? <span className="block text-xs text-slate-500">{c.sub_category}</span> : null}
                    </td>
                    <td className={tdClassName}>{c.scale?.name ?? t('comp.noScale')}</td>
                    <td className={tdClassName}>
                      <StatusBadge status={c.status} />
                      <span className="block text-xs text-slate-500">{c.is_active ? t('comp.active') : t('comp.inactive')}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager total={list.data.total} offset={offset} limit={COMPETENCY_PAGE_SIZE} onChange={setOffset} language={i18n.resolvedLanguage} />
        </>
      )}
      {selected ? (
        <CompetencyDetail
          competency={selected}
          canManage={canManage}
          onChanged={setSelected}
          onClose={() => setSelected(null)}
          onEdit={() => {
            setEditing(selected)
            setSelected(null)
          }}
        />
      ) : null}
      {editing ? <CompetencyDialog competency={editing === 'new' ? null : editing} onClose={() => setEditing(null)} /> : null}
    </div>
  )
}

const STATUS_TONE: Record<CompetencyStatus, string> = {
  draft: 'bg-amber-50 text-amber-900 ring-amber-200',
  approved: 'bg-emerald-50 text-emerald-900 ring-emerald-200',
}

/** Draft / approved badge (text always accompanies the colour). */
export function StatusBadge({ status }: { status: CompetencyStatus }) {
  const { t } = useTranslation()
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_TONE[status]}`}>
      {t(`comp.governance.${status}`)}
    </span>
  )
}

function CompetencyDetail({
  competency,
  canManage,
  onChanged,
  onClose,
  onEdit,
}: {
  competency: Competency
  canManage: boolean
  onChanged: (competency: Competency) => void
  onClose: () => void
  onEdit: () => void
}) {
  const { t, i18n } = useTranslation()
  const [action, setAction] = useState<'approve' | 'draft' | 'bands' | null>(null)
  if (action === 'bands') {
    return (
      <BandRequirementsDialog
        competency={competency}
        onClose={() => setAction(null)}
        onSaved={(saved) => {
          onChanged(saved)
          setAction(null)
        }}
      />
    )
  }
  if (action !== null) {
    return (
      <StatusDialog
        competency={competency}
        target={action === 'approve' ? 'approved' : 'draft'}
        onClose={() => setAction(null)}
        onSaved={(saved) => {
          onChanged(saved)
          setAction(null)
        }}
      />
    )
  }
  return (
    <Modal title={`${competency.name} (${competency.code})`} onClose={onClose} size="lg">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <StatusBadge status={competency.status} />
          {competency.status === 'approved' && competency.approved_at ? (
            <span className="text-slate-600">{t('comp.governance.approvedOn', { when: formatDateTime(competency.approved_at, i18n.resolvedLanguage) })}</span>
          ) : (
            <span className="text-slate-600">{t('comp.governance.draftHint')}</span>
          )}
        </div>
        <dl className="grid gap-3 sm:grid-cols-2">
          <Field label={t('comp.fields.category')}>{[competency.category, competency.sub_category].filter(Boolean).join(' › ') || '—'}</Field>
          <Field label={t('comp.fields.scale')}>{competency.scale?.name ?? t('comp.noScale')}</Field>
          <Field label={t('comp.fields.owner')}>{competency.owner_org_unit?.name ?? '—'}</Field>
          <Field label={t('comp.fields.source')}>{competency.source_ref ?? '—'}</Field>
        </dl>
        <dl className="grid gap-3">
          <Field label={t('comp.fields.description')}>{competency.description ?? '—'}</Field>
          <Field label={t('comp.fields.criteria')}>{competency.assessment_criteria ?? '—'}</Field>
          <Field label={t('comp.fields.applicability')}>{competency.applicability ?? '—'}</Field>
        </dl>
        <section aria-labelledby="bands-heading" className="space-y-2">
          <h3 id="bands-heading" className="font-semibold text-slate-900">{t('comp.bands.title')}</h3>
          {competency.band_requirements.length === 0 ? (
            <p className="text-sm text-slate-600">{t('comp.bands.none')}</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {competency.band_requirements.map((band) => (
                <li key={band.band_code}>
                  <span className="font-medium">{band.band_label ?? band.band_code}</span>: {levelText(band.required_level)}
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-slate-500">{t('comp.bands.note')}</p>
        </section>
        <div className="flex flex-wrap justify-end gap-2">
          {canManage ? (
            <>
              {competency.status === 'draft' ? (
                <button type="button" onClick={() => setAction('approve')} className={secondaryButtonClassName} disabled={!competency.is_active}>
                  {t('comp.governance.approve')}
                </button>
              ) : (
                <button type="button" onClick={() => setAction('draft')} className={secondaryButtonClassName}>
                  {t('comp.governance.returnToDraft')}
                </button>
              )}
              <button type="button" onClick={() => setAction('bands')} className={secondaryButtonClassName}>
                {t('comp.bands.edit')}
              </button>
              <button type="button" onClick={onEdit} className={secondaryButtonClassName}>
                <Pencil aria-hidden="true" className="size-4" />
                {t('comp.edit')}
              </button>
            </>
          ) : null}
          <button type="button" onClick={onClose} className={primaryButtonClassName}>
            {t('common.close')}
          </button>
        </div>
      </div>
    </Modal>
  )
}

function StatusDialog({
  competency,
  target,
  onClose,
  onSaved,
}: {
  competency: Competency
  target: CompetencyStatus
  onClose: () => void
  onSaved: (competency: Competency) => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  const reasonId = useId()
  const save = useCompetencyMutation(() =>
    competencyService.changeCompetencyStatus(competency.public_id, {
      version: competency.version,
      status: target,
      reason: text(reason),
    }),
  )
  const approving = target === 'approved'
  return (
    <Modal
      title={approving ? t('comp.governance.approveTitle', { name: competency.name }) : t('comp.governance.draftTitle', { name: competency.name })}
      description={approving ? t('comp.governance.approveHelp') : t('comp.governance.draftHelp')}
      onClose={onClose}
      busy={save.isPending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onSaved })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <FormField id={reasonId} label={approving ? t('comp.governance.note') : t('comp.governance.reason')}>
          <textarea id={reasonId} rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} className={inputClassName()} />
        </FormField>
        <DialogActions
          busy={save.isPending}
          onCancel={onClose}
          submitLabel={approving ? t('comp.governance.approve') : t('comp.governance.returnToDraft')}
        />
      </form>
    </Modal>
  )
}

interface BandDraft {
  key: string
  band_code: string
  band_label: string
  required_level: string
}

let bandKey = 0
const nextBandKey = () => `band-${(bandKey += 1)}`

/**
 * Edit the grade-band required levels. Bands are free text as written in the company
 * library (e.g. L6-L5); levels come from the competency's own scale. Changes are audited
 * and never alter recorded assessments.
 */
function BandRequirementsDialog({
  competency,
  onClose,
  onSaved,
}: {
  competency: Competency
  onClose: () => void
  onSaved: (competency: Competency) => void
}) {
  const { t } = useTranslation()
  const scales = useScales()
  const scale = (scales.data ?? []).find((s) => s.public_id === competency.scale?.public_id) ?? null
  const [rows, setRows] = useState<BandDraft[]>(() =>
    competency.band_requirements.map((band) => ({
      key: nextBandKey(),
      band_code: band.band_code,
      band_label: band.band_label ?? '',
      required_level: band.required_level?.public_id ?? '',
    })),
  )
  const save = useCompetencyMutation(() =>
    competencyService.setBandRequirements(competency.public_id, {
      version: competency.version,
      items: rows
        .filter((row) => row.band_code.trim() !== '')
        .map((row) => ({ band_code: row.band_code.trim(), band_label: text(row.band_label), required_level: row.required_level || null })),
    }),
  )
  const update = (key: string, change: Partial<BandDraft>) => setRows((all) => all.map((row) => (row.key === key ? { ...row, ...change } : row)))
  return (
    <Modal title={t('comp.bands.editTitle', { name: competency.name })} description={t('comp.bands.editHelp')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onSaved })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        {competency.scale === null ? <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{t('comp.bands.needsScale')}</p> : null}
        {rows.length === 0 ? <p className="text-sm text-slate-600">{t('comp.bands.none')}</p> : null}
        <ul className="space-y-3">
          {rows.map((row, index) => (
            <li key={row.key} className="grid gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
              <div className="space-y-1">
                <label htmlFor={`${row.key}-code`} className={labelClassName}>
                  {t('comp.bands.band')}
                </label>
                <input id={`${row.key}-code`} value={row.band_code} maxLength={30} onChange={(e) => update(row.key, { band_code: e.target.value })} className={inputClassName()} />
              </div>
              <div className="space-y-1">
                <label htmlFor={`${row.key}-label`} className={labelClassName}>
                  {t('comp.bands.label')}
                </label>
                <input id={`${row.key}-label`} value={row.band_label} maxLength={150} onChange={(e) => update(row.key, { band_label: e.target.value })} className={inputClassName()} />
              </div>
              <div className="space-y-1">
                <label htmlFor={`${row.key}-level`} className={labelClassName}>
                  {t('comp.bands.requiredLevel')}
                </label>
                <select
                  id={`${row.key}-level`}
                  value={row.required_level}
                  onChange={(e) => update(row.key, { required_level: e.target.value })}
                  className={inputClassName()}
                  disabled={scale === null}
                >
                  <option value="">{t('comp.bands.pending')}</option>
                  {(scale?.levels ?? []).map((level) => (
                    <option key={level.public_id} value={level.public_id}>
                      {levelText(level)}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => setRows((all) => all.filter((r) => r.key !== row.key))}
                className={secondaryButtonClassName}
                aria-label={t('comp.bands.remove', { band: row.band_code || String(index + 1) })}
              >
                <Trash2 aria-hidden="true" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={() => setRows((all) => [...all, { key: nextBandKey(), band_code: '', band_label: '', required_level: '' }])}
          className={secondaryButtonClassName}
        >
          <Plus aria-hidden="true" className="size-4" />
          {t('comp.bands.add')}
        </button>
        <p className="text-xs text-slate-500">{t('comp.bands.note')}</p>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

function CompetencyDialog({ competency, onClose }: { competency: Competency | null; onClose: () => void }) {
  const { t } = useTranslation()
  const scales = useScales()
  const [code, setCode] = useState(competency?.code ?? '')
  const [name, setName] = useState(competency?.name ?? '')
  const [category, setCategory] = useState(competency?.category ?? '')
  const [sub, setSub] = useState(competency?.sub_category ?? '')
  const [scale, setScale] = useState(competency?.scale?.public_id ?? '')
  const [description, setDescription] = useState(competency?.description ?? '')
  const [criteria, setCriteria] = useState(competency?.assessment_criteria ?? '')
  const [applicability, setApplicability] = useState(competency?.applicability ?? '')
  const [source, setSource] = useState(competency?.source_ref ?? '')
  const [active, setActive] = useState(competency?.is_active ?? true)
  const ids = { code: useId(), name: useId(), category: useId(), sub: useId(), scale: useId(), description: useId(), criteria: useId(), applicability: useId(), source: useId(), active: useId() }
  const save = useCompetencyMutation(() => {
    const body: Body = {
      code: code.trim(),
      name: name.trim(),
      category: text(category),
      sub_category: text(sub),
      scale: scale || null,
      description: text(description),
      assessment_criteria: text(criteria),
      applicability: text(applicability),
      source_ref: text(source),
    }
    return competency === null
      ? competencyService.createCompetency(body)
      : competencyService.updateCompetency(competency.public_id, { ...body, is_active: active, version: competency.version })
  })
  return (
    <Modal title={competency === null ? t('comp.create') : t('comp.edit')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.code} label={t('comp.fields.code')}>
            <input id={ids.code} value={code} onChange={(e) => setCode(e.target.value)} maxLength={50} className={inputClassName()} />
          </FormField>
          <FormField id={ids.name} label={t('comp.fields.name')}>
            <input id={ids.name} value={name} onChange={(e) => setName(e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          <FormField id={ids.category} label={t('comp.fields.category')}>
            <input id={ids.category} value={category} onChange={(e) => setCategory(e.target.value)} maxLength={150} className={inputClassName()} />
          </FormField>
          <FormField id={ids.sub} label={t('comp.fields.subCategory')}>
            <input id={ids.sub} value={sub} onChange={(e) => setSub(e.target.value)} maxLength={150} className={inputClassName()} />
          </FormField>
          <FormField id={ids.scale} label={t('comp.fields.scale')} hint={t('comp.scaleHint')}>
            <select id={ids.scale} value={scale} onChange={(e) => setScale(e.target.value)} className={inputClassName()}>
              <option value="">{t('comp.noScale')}</option>
              {(scales.data ?? []).map((s) => (
                <option key={s.public_id} value={s.public_id}>
                  {s.name}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.source} label={t('comp.fields.source')}>
            <input id={ids.source} value={source} onChange={(e) => setSource(e.target.value)} maxLength={200} className={inputClassName()} />
          </FormField>
        </div>
        <FormField id={ids.description} label={t('comp.fields.description')}>
          <textarea id={ids.description} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} className={inputClassName()} />
        </FormField>
        <FormField id={ids.criteria} label={t('comp.fields.criteria')}>
          <textarea id={ids.criteria} rows={2} value={criteria} onChange={(e) => setCriteria(e.target.value)} className={inputClassName()} />
        </FormField>
        <FormField id={ids.applicability} label={t('comp.fields.applicability')}>
          <input id={ids.applicability} value={applicability} onChange={(e) => setApplicability(e.target.value)} maxLength={1000} className={inputClassName()} />
        </FormField>
        {competency !== null ? (
          <label htmlFor={ids.active} className="flex items-center gap-2 text-sm">
            <input id={ids.active} type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="size-4 accent-brand-700" />
            {t('comp.active')}
          </label>
        ) : null}
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

// --------------------------------------------------------------------------- scales

function ScalesTab() {
  const { t } = useTranslation()
  const canManage = useHasPermission(PERMISSIONS.COMPETENCY_MANAGE)
  const scales = useScales()
  const [editing, setEditing] = useState<Scale | 'new' | null>(null)
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="max-w-3xl text-sm text-slate-600">{t('comp.scales.help')}</p>
        {canManage ? (
          <button type="button" onClick={() => setEditing('new')} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('comp.scales.create')}
          </button>
        ) : null}
      </div>
      {scales.isPending ? (
        <LoadingState />
      ) : scales.isError ? (
        <FeatureError error={scales.error} title={t('comp.scales.loadError')} onRetry={() => void scales.refetch()} />
      ) : scales.data.length === 0 ? (
        <EmptyState title={t('comp.scales.empty')} />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {scales.data.map((scale) => (
            <li key={scale.public_id} className={`${cardClassName} space-y-3`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-slate-900">{scale.name}</h3>
                  <p className="text-xs text-slate-500">
                    {scale.code} · {scale.gap_method === 'numeric' ? t('comp.scales.numeric') : t('comp.scales.ordinal')}
                    {scale.is_active ? '' : ` · ${t('comp.inactive')}`}
                  </p>
                </div>
                {canManage ? (
                  <button type="button" onClick={() => setEditing(scale)} className={secondaryButtonClassName}>
                    <Pencil aria-hidden="true" className="size-4" />
                    {t('comp.scales.edit')}
                  </button>
                ) : null}
              </div>
              <table className="min-w-full text-sm">
                <caption className="sr-only">{t('comp.scales.levelsCaption', { name: scale.name })}</caption>
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    <th scope="col" className="py-1 pr-2">{t('comp.scales.rank')}</th>
                    <th scope="col" className="py-1 pr-2">{t('comp.scales.level')}</th>
                    <th scope="col" className="py-1">{t('comp.scales.descriptor')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scale.levels.map((level) => (
                    <tr key={level.public_id}>
                      <td className="py-1 pr-2 tabular-nums">
                        {level.rank}
                        {scale.competent_rank === level.rank ? <span className="ml-1 text-xs text-emerald-700">({t('comp.scales.competentMark')})</span> : null}
                      </td>
                      <td className="py-1 pr-2">{levelText(level)}</td>
                      <td className="py-1 text-slate-600">{level.description ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <Field label={t('comp.scales.competentRank')}>{scale.competent_rank ?? t('comp.scales.notSet')}</Field>
                <Field label={t('comp.scales.planGap')}>{scale.plan_gap_steps ?? t('comp.scales.notSet')}</Field>
              </dl>
              {scale.source_note ? <p className="text-xs text-slate-500">{t('comp.scales.source', { note: scale.source_note })}</p> : null}
            </li>
          ))}
        </ul>
      )}
      {editing ? <ScaleDialog scale={editing === 'new' ? null : editing} onClose={() => setEditing(null)} /> : null}
    </div>
  )
}

function ScaleDialog({ scale, onClose }: { scale: Scale | null; onClose: () => void }) {
  const { t } = useTranslation()
  const [code, setCode] = useState(scale?.code ?? '')
  const [name, setName] = useState(scale?.name ?? '')
  const [gapMethod, setGapMethod] = useState(scale?.gap_method ?? 'ordinal')
  const [competent, setCompetent] = useState(scale?.competent_rank?.toString() ?? '')
  const [planGap, setPlanGap] = useState(scale?.plan_gap_steps?.toString() ?? '')
  const [note, setNote] = useState(scale?.source_note ?? '')
  const [levels, setLevels] = useState<(LevelInput & { key: string })[]>(() =>
    scale
      ? scale.levels.map((l) => ({ key: l.public_id, public_id: l.public_id, rank: l.rank, code: l.code, label: l.label, numeric_value: l.numeric_value, description: l.description }))
      : [{ key: 'new-1', rank: 1, code: 'L1', label: '', numeric_value: 1, description: null }],
  )
  const ids = { code: useId(), name: useId(), gap: useId(), competent: useId(), plan: useId(), note: useId() }
  const save = useCompetencyMutation(() => {
    const body: Body = {
      code: code.trim(),
      name: name.trim(),
      gap_method: gapMethod,
      competent_rank: competent.trim() === '' ? null : Number.parseInt(competent, 10),
      plan_gap_steps: planGap.trim() === '' ? null : Number.parseInt(planGap, 10),
      source_note: text(note),
      levels: levels.map((level) => ({
        public_id: level.public_id,
        rank: level.rank,
        numeric_value: level.numeric_value ?? null,
        code: level.code.trim(),
        label: level.label.trim(),
        description: level.description ? level.description.trim() || null : null,
      })),
    }
    return scale === null
      ? competencyService.createScale(body)
      : competencyService.updateScale(scale.public_id, { ...body, version: scale.version })
  })
  const update = (index: number, patch: Partial<LevelInput>) =>
    setLevels((current) => current.map((l, i) => (i === index ? { ...l, ...patch } : l)))
  return (
    <Modal title={scale === null ? t('comp.scales.create') : t('comp.scales.edit')} description={t('comp.scales.formHelp')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.code} label={t('comp.fields.code')}>
            <input id={ids.code} value={code} onChange={(e) => setCode(e.target.value)} maxLength={50} className={inputClassName()} />
          </FormField>
          <FormField id={ids.name} label={t('comp.fields.name')}>
            <input id={ids.name} value={name} onChange={(e) => setName(e.target.value)} maxLength={150} className={inputClassName()} />
          </FormField>
          <FormField id={ids.gap} label={t('comp.scales.gapMethod')} hint={t('comp.scales.gapHint')}>
            <select id={ids.gap} value={gapMethod} onChange={(e) => setGapMethod(e.target.value)} className={inputClassName()}>
              <option value="ordinal">{t('comp.scales.ordinal')}</option>
              <option value="numeric">{t('comp.scales.numeric')}</option>
            </select>
          </FormField>
          <FormField id={ids.competent} label={t('comp.scales.competentRank')} hint={t('comp.scales.competentHint')}>
            <input id={ids.competent} type="number" min={0} value={competent} onChange={(e) => setCompetent(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.plan} label={t('comp.scales.planGap')} hint={t('comp.scales.planHint')}>
            <input id={ids.plan} type="number" min={1} value={planGap} onChange={(e) => setPlanGap(e.target.value)} className={inputClassName()} />
          </FormField>
          <FormField id={ids.note} label={t('comp.scales.sourceNote')}>
            <input id={ids.note} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} className={inputClassName()} />
          </FormField>
        </div>
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-slate-900">{t('comp.scales.levels')}</legend>
          {levels.map((level, index) => (
            <div key={level.key} className="grid items-end gap-2 rounded-md border border-slate-200 p-2 sm:grid-cols-[4rem_5rem_1fr_5rem_auto]">
              <label className="space-y-1 text-xs">
                {t('comp.scales.rank')}
                <input type="number" min={0} value={level.rank} onChange={(e) => update(index, { rank: Number.parseInt(e.target.value || '0', 10) })} className={inputClassName()} />
              </label>
              <label className="space-y-1 text-xs">
                {t('comp.fields.code')}
                <input value={level.code} onChange={(e) => update(index, { code: e.target.value })} maxLength={30} className={inputClassName()} />
              </label>
              <label className="space-y-1 text-xs">
                {t('comp.scales.label')}
                <input value={level.label} onChange={(e) => update(index, { label: e.target.value })} maxLength={150} className={inputClassName()} />
              </label>
              <label className="space-y-1 text-xs">
                {t('comp.scales.numericValue')}
                <input
                  type="number"
                  value={level.numeric_value ?? ''}
                  onChange={(e) => update(index, { numeric_value: e.target.value === '' ? null : Number(e.target.value) })}
                  className={inputClassName()}
                />
              </label>
              <button
                type="button"
                onClick={() => setLevels((c) => c.filter((_, i) => i !== index))}
                aria-label={t('comp.scales.removeLevel', { code: level.code })}
                disabled={levels.length === 1}
                className="rounded p-2 text-red-700 hover:bg-red-50 disabled:opacity-40"
              >
                <Trash2 aria-hidden="true" className="size-4" />
              </button>
              <label className="space-y-1 text-xs sm:col-span-5">
                {t('comp.scales.descriptor')}
                <input value={level.description ?? ''} onChange={(e) => update(index, { description: e.target.value })} maxLength={1000} className={inputClassName()} />
              </label>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setLevels((c) => {
                const rank = c.reduce((max, l) => Math.max(max, l.rank), 0) + 1
                return [...c, { key: `new-${Date.now()}`, rank, code: `L${rank}`, label: '', numeric_value: rank, description: null }]
              })
            }
            className={secondaryButtonClassName}
          >
            <Plus aria-hidden="true" className="size-4" />
            {t('comp.scales.addLevel')}
          </button>
        </fieldset>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}
