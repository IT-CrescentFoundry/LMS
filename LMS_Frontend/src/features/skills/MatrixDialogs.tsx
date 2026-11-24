import { ArrowDown, ArrowUp, Trash2 } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Field } from '../../components/FeatureState'
import { inputClassName, labelClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import {
  DesignationSelect,
  EmployeePicker,
  FunctionalRoleSelect,
  LocationSelect,
  UnitSelect,
} from '../../components/Pickers'
import { formatDate, formatDateTime, todayIsoDate } from '../../lib/format'
import { competencyService } from '../../services/competencyService'
import {
  ASSESSMENT_METHODS,
  type Body,
  type Matrix,
  type MatrixCell,
  type MatrixItem,
  type MatrixItemInput,
  type MatrixRow,
} from '../../types/competency'
import type { EmployeeRef } from '../../types/training'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { DialogActions, DialogError, FormField } from '../training/EventDialogs'
import { useAssessments, useCompetencies, useCompetencyMutation, useScales } from './competencyQueries'
import { GapBadge } from './SkillParts'
import { levelText } from './skillLabels'

const text = (value: string): string | null => (value.trim() === '' ? null : value.trim())

// -------------------------------------------------------------------- matrix form

export function MatrixFormDialog({
  matrix,
  onClose,
  onSaved,
}: {
  matrix: Matrix | null
  onClose: () => void
  onSaved?: (matrix: Matrix) => void
}) {
  const { t } = useTranslation()
  const scales = useScales()
  const [code, setCode] = useState(matrix?.code ?? '')
  const [name, setName] = useState(matrix?.name ?? '')
  const [description, setDescription] = useState(matrix?.description ?? '')
  const [scale, setScale] = useState(matrix?.scale.public_id ?? '')
  const [unit, setUnit] = useState(matrix?.org_unit?.public_id ?? '')
  const [location, setLocation] = useState(matrix?.location?.public_id ?? '')
  const [designation, setDesignation] = useState(matrix?.designation?.public_id ?? '')
  const [role, setRole] = useState(matrix?.functional_role?.public_id ?? '')
  const [margin, setMargin] = useState(String(matrix?.risk_medium_margin ?? 1))
  const [active, setActive] = useState(matrix?.is_active ?? true)
  const ids = { code: useId(), name: useId(), description: useId(), scale: useId(), margin: useId(), active: useId() }
  const save = useCompetencyMutation(() => {
    const body: Body = {
      code: code.trim(),
      name: name.trim(),
      description: text(description),
      org_unit: text(unit),
      location: text(location),
      designation: text(designation),
      functional_role: text(role),
      risk_medium_margin: margin.trim() === '' ? null : Number.parseInt(margin, 10),
    }
    if (matrix === null) return competencyService.createMatrix({ ...body, scale })
    const changes: Body = { version: matrix.version, ...body, is_active: active }
    if (scale !== matrix.scale.public_id) changes.scale = scale
    return competencyService.updateMatrix(matrix.public_id, changes)
  })
  return (
    <Modal title={matrix === null ? t('skills.matrix.create') : t('skills.matrix.edit')} description={t('skills.matrix.formHelp')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: (saved) => (onSaved ? onSaved(saved) : onClose()) })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id={ids.code} label={t('skills.fields.code')}>
            <input id={ids.code} value={code} onChange={(e) => setCode(e.target.value)} maxLength={50} className={inputClassName()} />
          </FormField>
          <FormField id={ids.name} label={t('skills.fields.name')}>
            <input id={ids.name} value={name} onChange={(e) => setName(e.target.value)} maxLength={250} className={inputClassName()} />
          </FormField>
          <FormField id={ids.scale} label={t('skills.fields.scale')} hint={t('skills.matrix.scaleHint')}>
            <select id={ids.scale} value={scale} onChange={(e) => setScale(e.target.value)} className={inputClassName()}>
              <option value="">{t('skills.matrix.chooseScale')}</option>
              {(scales.data ?? []).map((s) => (
                <option key={s.public_id} value={s.public_id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </FormField>
          <FormField id={ids.margin} label={t('skills.fields.riskMargin')} hint={t('skills.matrix.riskHint')}>
            <input id={ids.margin} type="number" min={0} max={100} value={margin} onChange={(e) => setMargin(e.target.value)} className={inputClassName()} />
          </FormField>
          <UnitSelect label={t('skills.fields.unit')} value={unit} onChange={setUnit} allLabel={t('skills.matrix.anyScope')} />
          <LocationSelect label={t('skills.fields.location')} value={location} onChange={setLocation} allLabel={t('skills.matrix.anyScope')} />
          <DesignationSelect
            label={t('skills.fields.designation')}
            value={designation}
            onChange={setDesignation}
            allLabel={t('skills.matrix.anyScope')}
            current={matrix?.designation ?? null}
          />
          <FunctionalRoleSelect
            label={t('skills.fields.functionalRole')}
            value={role}
            onChange={setRole}
            allLabel={t('skills.matrix.anyScope')}
            current={matrix?.functional_role ?? null}
          />
        </div>
        <p className="text-xs text-slate-600">{t('skills.matrix.scopeReferenceHint')}</p>
        <FormField id={ids.description} label={t('skills.fields.description')}>
          <textarea id={ids.description} rows={2} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} className={inputClassName()} />
        </FormField>
        {matrix !== null ? (
          <label htmlFor={ids.active} className="flex items-center gap-2 text-sm">
            <input id={ids.active} type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="size-4 accent-brand-700" />
            {t('skills.matrix.active')}
          </label>
        ) : null}
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

// --------------------------------------------------------------------- items editor

interface ItemDraft {
  competency: string
  name: string
  code: string
  required_level: string
  required_headcount: string
  group_label: string
}

function draftItems(items: readonly MatrixItem[]): ItemDraft[] {
  return items.map((item) => ({
    competency: item.competency.public_id,
    name: item.competency.name,
    code: item.competency.code,
    required_level: item.required_level?.public_id ?? '',
    required_headcount: item.required_headcount?.toString() ?? '',
    group_label: item.group_label ?? '',
  }))
}

export function MatrixItemsDialog({ matrix, onClose }: { matrix: Matrix; onClose: () => void }) {
  const { t } = useTranslation()
  const [rows, setRows] = useState<ItemDraft[]>(() => draftItems(matrix.items))
  const [q, setQ] = useState('')
  const search = useCompetencies({ q: q.trim() || undefined }, 0, 20)
  const searchId = useId()
  const save = useCompetencyMutation(() => {
    const items: MatrixItemInput[] = rows.map((row, index) => ({
      competency: row.competency,
      required_level: row.required_level || null,
      required_headcount: row.required_headcount.trim() === '' ? null : Number.parseInt(row.required_headcount, 10),
      group_label: text(row.group_label),
      display_order: index,
    }))
    return competencyService.setItems(matrix.public_id, { version: matrix.version, items })
  })
  const update = (index: number, patch: Partial<ItemDraft>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  const move = (index: number, delta: number) =>
    setRows((current) => {
      const next = [...current]
      const target = index + delta
      if (target < 0 || target >= next.length) return current
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  const present = new Set(rows.map((r) => r.competency))
  return (
    <Modal title={t('skills.items.title', { name: matrix.name })} description={t('skills.items.help')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        {rows.length === 0 ? <p className="text-sm text-slate-600">{t('skills.items.none')}</p> : null}
        <ul className="space-y-3">
          {rows.map((row, index) => (
            <li key={row.competency} className="space-y-2 rounded-lg border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-900">
                  {row.name} <span className="text-xs text-slate-500">({row.code})</span>
                </p>
                <div className="flex gap-1">
                  <button type="button" onClick={() => move(index, -1)} aria-label={t('skills.items.up', { name: row.name })} className="rounded p-1 hover:bg-slate-100">
                    <ArrowUp aria-hidden="true" className="size-4" />
                  </button>
                  <button type="button" onClick={() => move(index, 1)} aria-label={t('skills.items.down', { name: row.name })} className="rounded p-1 hover:bg-slate-100">
                    <ArrowDown aria-hidden="true" className="size-4" />
                  </button>
                  <button type="button" onClick={() => setRows((c) => c.filter((_, i) => i !== index))} aria-label={t('skills.items.remove', { name: row.name })} className="rounded p-1 text-red-700 hover:bg-red-50">
                    <Trash2 aria-hidden="true" className="size-4" />
                  </button>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <label className="space-y-1 text-xs text-slate-700">
                  {t('skills.fields.requiredLevel')}
                  <select value={row.required_level} onChange={(e) => update(index, { required_level: e.target.value })} className={inputClassName()}>
                    <option value="">{t('skills.items.pending')}</option>
                    {matrix.scale.levels.map((level) => (
                      <option key={level.public_id} value={level.public_id}>
                        {levelText(level)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1 text-xs text-slate-700">
                  {t('skills.fields.requiredHeadcount')}
                  <input type="number" min={0} value={row.required_headcount} onChange={(e) => update(index, { required_headcount: e.target.value })} className={inputClassName()} />
                </label>
                <label className="space-y-1 text-xs text-slate-700">
                  {t('skills.fields.group')}
                  <input value={row.group_label} onChange={(e) => update(index, { group_label: e.target.value })} maxLength={150} className={inputClassName()} />
                </label>
              </div>
            </li>
          ))}
        </ul>
        <div className="space-y-2 rounded-lg bg-slate-50 p-3">
          <label htmlFor={searchId} className={labelClassName}>
            {t('skills.items.add')}
          </label>
          <input id={searchId} type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('skills.items.searchPlaceholder')} className={inputClassName()} />
          {search.data ? (
            <ul className="max-h-44 overflow-y-auto rounded-md border border-slate-200 bg-white text-sm">
              {search.data.items
                .filter((c) => !present.has(c.public_id))
                .map((c) => (
                  <li key={c.public_id}>
                    <button
                      type="button"
                      onClick={() =>
                        setRows((current) => [
                          ...current,
                          { competency: c.public_id, name: c.name, code: c.code, required_level: '', required_headcount: '', group_label: c.category ?? '' },
                        ])
                      }
                      className="w-full px-3 py-1.5 text-left hover:bg-slate-50"
                    >
                      {c.name} <span className="text-slate-500">({c.code})</span>
                    </button>
                  </li>
                ))}
            </ul>
          ) : null}
        </div>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------------ members

export function MembersDialog({
  matrix,
  members,
  onClose,
}: {
  matrix: Matrix
  members: EmployeeRef[]
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [add, setAdd] = useState<EmployeeRef[]>([])
  const [remove, setRemove] = useState<Set<string>>(new Set())
  const save = useCompetencyMutation(() =>
    competencyService.setMembers(matrix.public_id, { add: add.map((e) => e.public_id), remove: [...remove] }),
  )
  return (
    <Modal title={t('skills.members.title', { name: matrix.name })} description={t('skills.members.help')} onClose={onClose} busy={save.isPending} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate(undefined, { onSuccess: onClose })
        }}
        className="space-y-4"
        noValidate
      >
        <DialogError error={save.error} />
        <EmployeePicker label={t('skills.members.add')} selected={add} onChange={setAdd} multiple />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t('skills.members.current', { count: members.length })}</legend>
          {members.length === 0 ? <p className="text-sm text-slate-600">{t('skills.members.none')}</p> : null}
          <ul className="max-h-60 space-y-1 overflow-y-auto">
            {members.map((member) => (
              <li key={member.public_id}>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={remove.has(member.public_id)}
                    onChange={(e) =>
                      setRemove((current) => {
                        const next = new Set(current)
                        if (e.target.checked) next.add(member.public_id)
                        else next.delete(member.public_id)
                        return next
                      })
                    }
                    className="size-4 accent-red-700"
                  />
                  {t('skills.members.removeLabel', { name: member.name, code: member.employee_code })}
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
        <DialogActions busy={save.isPending} onCancel={onClose} submitLabel={t('common.save')} />
      </form>
    </Modal>
  )
}

// --------------------------------------------------------------- assessment panel

/** Competency detail, assessment history and (with competency.assess) a new assessment. */
export function AssessmentPanel({
  matrix,
  row,
  item,
  cell,
  onClose,
}: {
  matrix: Matrix
  row: MatrixRow
  item: MatrixItem
  cell: MatrixCell
  onClose: () => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canAssess = useHasPermission(PERMISSIONS.COMPETENCY_ASSESS)
  const history = useAssessments(row.employee.public_id, item.competency.public_id)
  const [level, setLevel] = useState('')
  const [date, setDate] = useState(todayIsoDate())
  const [method, setMethod] = useState<string>('assessor_rating')
  const [assessor, setAssessor] = useState<EmployeeRef[]>([])
  const [assessorName, setAssessorName] = useState('')
  const [evidence, setEvidence] = useState('')
  const [saved, setSaved] = useState(false)
  const ids = { level: useId(), date: useId(), method: useId(), name: useId(), evidence: useId() }
  const record = useCompetencyMutation(() =>
    competencyService.recordAssessment({
      employee: row.employee.public_id,
      competency: item.competency.public_id,
      level,
      assessed_on: date,
      method,
      assessor_employee: assessor[0]?.public_id ?? null,
      assessor_name: text(assessorName),
      evidence: text(evidence),
      matrix: matrix.public_id,
    }),
  )
  return (
    <Modal title={`${item.competency.name} — ${row.employee.name}`} onClose={onClose} busy={record.isPending} size="lg">
      <div className="space-y-5">
        <dl className="grid gap-3 sm:grid-cols-3">
          <Field label={t('skills.fields.requiredLevel')}>{levelText(cell.required_level)}</Field>
          <Field label={t('skills.fields.assessedLevel')}>
            {levelText(cell.assessed_level)}
            {cell.assessed_on ? <span className="block text-xs text-slate-500">{formatDate(cell.assessed_on, language)}</span> : null}
          </Field>
          <Field label={t('skills.fields.gap')}>
            <GapBadge status={cell.gap.status} steps={cell.gap.gap_steps} />
            {cell.gap.gap_value !== null ? <span className="block text-xs text-slate-500">{t('skills.gap.value', { value: cell.gap.gap_value })}</span> : null}
          </Field>
        </dl>
        <section aria-labelledby="history-heading" className="space-y-2">
          <h3 id="history-heading" className="font-semibold text-slate-900">{t('skills.history.title')}</h3>
          {history.isPending ? (
            <LoadingState />
          ) : history.isError ? (
            <p className="text-sm text-red-800">{t('skills.history.loadError')}</p>
          ) : history.data.length === 0 ? (
            <p className="text-sm text-slate-600">{t('skills.history.empty')}</p>
          ) : (
            <ol className="space-y-2">
              {history.data.map((a) => (
                <li key={a.public_id} className="rounded-md border border-slate-200 p-2 text-sm">
                  <p className="font-medium text-slate-900">
                    {levelText(a.level)} · {formatDate(a.assessed_on, language)}
                  </p>
                  <p className="text-xs text-slate-600">
                    {(ASSESSMENT_METHODS as readonly string[]).includes(a.method)
                      ? t(`skills.method.${a.method as (typeof ASSESSMENT_METHODS)[number]}`)
                      : a.method}
                    {a.assessor ? ` · ${a.assessor.name}` : a.assessor_name ? ` · ${a.assessor_name}` : ''}
                    {` · ${t('skills.history.recorded', { when: formatDateTime(a.recorded_at, language) })}`}
                  </p>
                  {a.evidence ? <p className="mt-1 text-xs text-slate-700">{a.evidence}</p> : null}
                </li>
              ))}
            </ol>
          )}
        </section>
        {canAssess ? (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (!level) return
              record.mutate(undefined, {
                onSuccess: () => {
                  setSaved(true)
                  setEvidence('')
                },
              })
            }}
            className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
            noValidate
          >
            <h3 className="font-semibold text-slate-900">{t('skills.assess.title')}</h3>
            <p className="text-xs text-slate-600">{t('skills.assess.help')}</p>
            <DialogError error={record.error} />
            {saved ? <p role="status" className="text-sm text-emerald-800">{t('skills.assess.saved')}</p> : null}
            <div className="grid gap-3 sm:grid-cols-3">
              <FormField id={ids.level} label={t('skills.fields.assessedLevel')}>
                <select id={ids.level} required value={level} onChange={(e) => setLevel(e.target.value)} className={inputClassName()}>
                  <option value="">{t('skills.assess.chooseLevel')}</option>
                  {matrix.scale.levels.map((l) => (
                    <option key={l.public_id} value={l.public_id}>
                      {levelText(l)}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField id={ids.date} label={t('skills.fields.assessedOn')}>
                <input id={ids.date} type="date" max={todayIsoDate()} value={date} onChange={(e) => setDate(e.target.value)} className={inputClassName()} />
              </FormField>
              <FormField id={ids.method} label={t('skills.fields.method')}>
                <select id={ids.method} value={method} onChange={(e) => setMethod(e.target.value)} className={inputClassName()}>
                  {ASSESSMENT_METHODS.map((m) => (
                    <option key={m} value={m}>
                      {t(`skills.method.${m}`)}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>
            <EmployeePicker label={t('skills.fields.assessor')} selected={assessor} onChange={setAssessor} />
            <FormField id={ids.name} label={t('skills.fields.assessorName')}>
              <input id={ids.name} value={assessorName} onChange={(e) => setAssessorName(e.target.value)} maxLength={200} className={inputClassName()} />
            </FormField>
            <FormField id={ids.evidence} label={t('skills.fields.evidence')}>
              <textarea id={ids.evidence} rows={2} maxLength={2000} value={evidence} onChange={(e) => setEvidence(e.target.value)} className={inputClassName()} />
            </FormField>
            <DialogActions busy={record.isPending} onCancel={onClose} submitLabel={t('skills.assess.submit')} />
          </form>
        ) : (
          <div className="flex justify-end">
            <button type="button" onClick={onClose} className={secondaryButtonClassName}>
              {t('common.close')}
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
