import { useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { labelClassName } from '../../components/formStyles'
import { Modal } from '../../components/Modal'
import { formatDate } from '../../lib/format'
import { organisationService, translationChanges } from '../../services/organisationService'
import type { OrgUnit, OrgUnitWrite, Ref, UnitCorrection, UnitCreate } from '../../types/organisation'
import { localName } from './names'
import {
  ChangeError,
  DialogActions,
  SelectField,
  TextAreaField,
  TextField,
  TranslationFields,
  type SuccessNotice,
} from './OrgParts'
import { useLocations, useOrgMutation, useReloadAndClose as useReload, useUnitTypes } from './orgQueries'
import { descendantIds, type TreeIndex } from './tree'

export type UnitDialogState =
  | { kind: 'create'; parent: Ref | null }
  | { kind: 'correct' | 'move' | 'close' | 'reopen'; unit: OrgUnit }

interface DialogProps {
  onClose: () => void
  onDone: (notice: SuccessNotice, unit: OrgUnit) => void
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

// --------------------------------------------------------- create / correct

export function UnitFormDialog({
  mode,
  unit,
  parent,
  onClose,
  onDone,
}: DialogProps & { mode: 'create' | 'correct'; unit?: OrgUnit; parent?: Ref | null }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const unitTypes = useUnitTypes()
  const locations = useLocations(false)
  const [code, setCode] = useState(unit?.code ?? '')
  const [name, setName] = useState(unit?.name ?? '')
  const [shortName, setShortName] = useState(unit?.short_name ?? '')
  const [typeId, setTypeId] = useState(unit?.unit_type.public_id ?? '')
  const [locationId, setLocationId] = useState(unit?.location?.public_id ?? '')
  const [effectiveFrom, setEffectiveFrom] = useState(unit?.effective_from ?? '')
  const [externalRef, setExternalRef] = useState(unit?.external_ref ?? '')
  const [translations, setTranslations] = useState<Record<string, string>>({ ...(unit?.translations ?? {}) })
  const [reason, setReason] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const [nothingChanged, setNothingChanged] = useState(false)
  const reload = useReload(onClose)

  const mutation = useOrgMutation(
    (change: { create: UnitCreate } | { correct: UnitCorrection }): Promise<OrgUnitWrite> =>
      'create' in change
        ? organisationService.createUnit(change.create)
        : organisationService.correctUnit(unit?.public_id ?? '', change.correct),
  )

  const typeOptions = (unitTypes.data ?? [])
    .filter((type) => type.is_active || type.public_id === unit?.unit_type.public_id)
    .map((type) => ({ value: type.public_id, label: localName(type, language) }))
  const locationOptions = (locations.data ?? []).map((location) => ({
    value: location.public_id,
    label: `${location.name} (${location.code})`,
  }))
  if (unit?.location && !locationOptions.some((option) => option.value === unit.location?.public_id)) {
    locationOptions.push({ value: unit.location.public_id, label: `${unit.location.name} (${unit.location.code})` })
  }

  const required = t('org.errors.required')
  const errors = {
    code: code.trim() === '' ? required : undefined,
    name: name.trim() === '' ? required : undefined,
    type: typeId === '' ? required : undefined,
  }

  function buildCorrection(): UnitCorrection | null {
    if (!unit) return null
    const body: Omit<UnitCorrection, 'version'> = {}
    if (code.trim() !== unit.code) body.code = code.trim()
    if (name.trim() !== unit.name) body.name = name.trim()
    if (blankToNull(shortName) !== unit.short_name) body.short_name = blankToNull(shortName)
    if (typeId !== unit.unit_type.public_id) body.unit_type_id = typeId
    if ((locationId || null) !== (unit.location?.public_id ?? null)) body.location_id = locationId || null
    if ((effectiveFrom || null) !== unit.effective_from) body.effective_from = effectiveFrom || null
    if (blankToNull(externalRef) !== unit.external_ref) body.external_ref = blankToNull(externalRef)
    const changedTranslations = translationChanges(unit.translations, translations)
    if (changedTranslations) body.translations = changedTranslations
    if (Object.keys(body).length === 0) return null
    return { ...body, version: unit.version, reason: blankToNull(reason) }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name || errors.type) return
    let change: { create: UnitCreate } | { correct: UnitCorrection }
    if (mode === 'create') {
      change = { create: {
        code: code.trim(),
        name: name.trim(),
        short_name: blankToNull(shortName),
        unit_type_id: typeId,
        location_id: locationId || null,
        parent_id: parent?.public_id ?? null,
        effective_from: effectiveFrom || null,
        external_ref: blankToNull(externalRef),
        translations: translationChanges({}, translations) ?? {},
      } }
    } else {
      const correction = buildCorrection()
      if (correction === null) {
        setNothingChanged(true)
        return
      }
      change = { correct: correction }
    }
    setNothingChanged(false)
    mutation.mutate(change, {
      onSuccess: (result) =>
        onDone(
          {
            message: t(mode === 'create' ? 'org.structure.messages.created' : 'org.structure.messages.corrected', {
              name: result.unit.name,
            }),
            warnings: result.warnings,
          },
          result.unit,
        ),
    })
  }

  const title =
    mode === 'correct' && unit
      ? t('org.structure.dialogs.correctTitle', { name: localName(unit, language) })
      : parent
        ? t('org.structure.dialogs.createChildTitle', { name: localName(parent, language) })
        : t('org.structure.dialogs.createRootTitle')

  return (
    <Modal
      title={title}
      description={mode === 'correct' ? t('org.structure.dialogs.correctHint') : undefined}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t('org.fields.code')}
            value={code}
            onChange={setCode}
            required
            maxLength={50}
            hint={t('org.hints.code')}
            error={showErrors ? errors.code : undefined}
            autoFocus
          />
          <TextField
            label={t('org.fields.name')}
            value={name}
            onChange={setName}
            required
            maxLength={200}
            error={showErrors ? errors.name : undefined}
          />
          <TextField label={t('org.fields.shortName')} value={shortName} onChange={setShortName} maxLength={50} />
          <SelectField
            label={t('org.fields.unitType')}
            value={typeId}
            onChange={setTypeId}
            options={typeOptions}
            emptyLabel={t('org.common.choose')}
            required
            error={showErrors ? errors.type : undefined}
          />
          <SelectField
            label={t('org.fields.location')}
            value={locationId}
            onChange={setLocationId}
            options={locationOptions}
            emptyLabel={t('org.common.none')}
          />
          <TextField
            label={t('org.fields.effectiveFrom')}
            type="date"
            value={effectiveFrom}
            onChange={setEffectiveFrom}
            hint={t('org.hints.effectiveFrom')}
          />
          <TextField
            label={t('org.fields.externalRef')}
            value={externalRef}
            onChange={setExternalRef}
            maxLength={100}
            hint={t('org.hints.externalRef')}
          />
          {mode === 'create' ? (
            <div className="space-y-1.5">
              <p className={labelClassName}>{t('org.fields.parent')}</p>
              <p className="rounded-md bg-slate-50 px-3 py-2.5 text-sm text-slate-800 ring-1 ring-slate-200">
                {parent ? `${localName(parent, language)} (${parent.code})` : t('org.common.topLevel')}
              </p>
            </div>
          ) : null}
        </div>
        <TranslationFields values={translations} onChange={setTranslations} />
        {mode === 'correct' ? (
          <TextAreaField
            label={t('org.fields.reason')}
            value={reason}
            onChange={setReason}
            maxLength={500}
            hint={t('org.hints.reason')}
          />
        ) : null}
        {nothingChanged ? (
          <p role="status" className="text-sm text-slate-700">
            {t('org.messages.noChanges')}
          </p>
        ) : null}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={mode === 'create' ? t('org.actions.create') : t('org.actions.saveCorrection')}
        />
      </form>
    </Modal>
  )
}

// -------------------------------------------------------------------- move

const ROOT = '__top_level__'

export function MoveUnitDialog({
  unit,
  index,
  onClose,
  onDone,
}: DialogProps & { unit: OrgUnit; index: TreeIndex }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [filter, setFilter] = useState('')
  const [target, setTarget] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [step, setStep] = useState<'form' | 'confirm'>('form')
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReload(onClose)
  const mutation = useOrgMutation((body: { version: number; new_parent_id: string | null; effective_date: string }) =>
    organisationService.moveUnit(unit.public_id, body),
  )

  const excluded = useMemo(() => {
    const set = descendantIds(index, unit.public_id)
    set.add(unit.public_id)
    return set
  }, [index, unit.public_id])

  const candidates = [...index.byId.values()]
    .filter((node) => !excluded.has(node.public_id) && node.status === 'active')
    .map((node) => ({ value: node.public_id, label: `${localName(node, language)} (${node.code})` }))
    .filter((option) => option.label.toLocaleLowerCase().includes(filter.trim().toLocaleLowerCase()))
    .sort((a, b) => a.label.localeCompare(b.label))

  const targetLabel =
    target === ROOT
      ? t('org.common.topLevel')
      : candidates.find((option) => option.value === target)?.label ??
        (index.byId.get(target) ? `${localName(index.byId.get(target)!, language)}` : '')

  const errors = {
    target: target === '' ? t('org.errors.chooseParent') : undefined,
    date: effectiveDate === '' ? t('org.errors.required') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'form') {
      setShowErrors(true)
      if (errors.target || errors.date) return
      setStep('confirm')
      return
    }
    mutation.mutate(
      { version: unit.version, new_parent_id: target === ROOT ? null : target, effective_date: effectiveDate },
      {
        onSuccess: (result) =>
          onDone(
            {
              message: t('org.structure.messages.moved', {
                name: result.unit.name,
                date: formatDate(effectiveDate, language),
              }),
              warnings: result.warnings,
            },
            result.unit,
          ),
      },
    )
  }

  const unitName = localName(unit, language)
  return (
    <Modal
      title={t('org.structure.dialogs.moveTitle', { name: unitName })}
      description={t('org.structure.dialogs.moveHint')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {step === 'form' ? (
          <>
            <p className="text-sm text-slate-700">
              {t('org.structure.dialogs.currentParent', {
                parent: unit.parent ? localName(unit.parent, language) : t('org.common.topLevel'),
              })}
            </p>
            <TextField
              label={t('org.structure.dialogs.parentFilter')}
              value={filter}
              onChange={setFilter}
              maxLength={100}
              autoFocus
            />
            <SelectField
              label={t('org.fields.newParent')}
              value={target}
              onChange={setTarget}
              options={[{ value: ROOT, label: t('org.common.topLevel') }, ...candidates]}
              size={8}
              required
              hint={t('org.structure.dialogs.parentListHint')}
              error={showErrors ? errors.target : undefined}
            />
            <TextField
              label={t('org.fields.effectiveDate')}
              type="date"
              value={effectiveDate}
              onChange={setEffectiveDate}
              required
              hint={t('org.structure.dialogs.moveDateHint')}
              error={showErrors ? errors.date : undefined}
            />
          </>
        ) : (
          <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
            <p className="font-medium">
              {t('org.structure.dialogs.moveConfirm', {
                name: unitName,
                parent: targetLabel,
                date: formatDate(effectiveDate, language),
              })}
            </p>
            <p>{t('org.structure.dialogs.historyKept')}</p>
          </div>
        )}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={step === 'confirm' && !mutation.isPending ? () => setStep('form') : onClose}
          cancelLabel={step === 'confirm' ? t('org.actions.back') : undefined}
          busy={mutation.isPending}
          submitLabel={step === 'form' ? t('org.actions.continue') : t('org.actions.confirmMove')}
        />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------- close

export function CloseUnitDialog({ unit, onClose, onDone }: DialogProps & { unit: OrgUnit }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [effectiveDate, setEffectiveDate] = useState('')
  const [reason, setReason] = useState('')
  const [step, setStep] = useState<'form' | 'confirm'>('form')
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReload(onClose)
  const mutation = useOrgMutation((body: { version: number; effective_date: string; reason: string | null }) =>
    organisationService.closeUnit(unit.public_id, body),
  )
  const dateError = effectiveDate === '' ? t('org.errors.required') : undefined
  const unitName = localName(unit, language)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (step === 'form') {
      setShowErrors(true)
      if (dateError) return
      setStep('confirm')
      return
    }
    mutation.mutate(
      { version: unit.version, effective_date: effectiveDate, reason: blankToNull(reason) },
      {
        onSuccess: (result) =>
          onDone(
            {
              message: t('org.structure.messages.closed', {
                name: result.unit.name,
                date: formatDate(effectiveDate, language),
              }),
              warnings: result.warnings,
            },
            result.unit,
          ),
      },
    )
  }

  return (
    <Modal
      title={t('org.structure.dialogs.closeTitle', { name: unitName })}
      description={t('org.structure.dialogs.closeHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {step === 'form' ? (
          <>
            <TextField
              label={t('org.fields.closureDate')}
              type="date"
              value={effectiveDate}
              onChange={setEffectiveDate}
              required
              hint={t('org.structure.dialogs.closeDateHint')}
              error={showErrors ? dateError : undefined}
              autoFocus
            />
            <TextAreaField label={t('org.fields.reason')} value={reason} onChange={setReason} maxLength={500} />
          </>
        ) : (
          <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-950">
            <p className="font-medium">
              {t('org.structure.dialogs.closeConfirm', { name: unitName, date: formatDate(effectiveDate, language) })}
            </p>
            <p>{t('org.structure.dialogs.historyKept')}</p>
          </div>
        )}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={step === 'confirm' && !mutation.isPending ? () => setStep('form') : onClose}
          cancelLabel={step === 'confirm' ? t('org.actions.back') : undefined}
          busy={mutation.isPending}
          tone={step === 'confirm' ? 'danger' : 'primary'}
          submitLabel={step === 'form' ? t('org.actions.continue') : t('org.actions.confirmClose')}
        />
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ reopen

export function ReopenUnitDialog({ unit, onClose, onDone }: DialogProps & { unit: OrgUnit }) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [reason, setReason] = useState('')
  const reload = useReload(onClose)
  const mutation = useOrgMutation((body: { version: number; reason: string | null }) =>
    organisationService.reopenUnit(unit.public_id, body),
  )
  const unitName = localName(unit, language)

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      { version: unit.version, reason: blankToNull(reason) },
      {
        onSuccess: (result) =>
          onDone(
            { message: t('org.structure.messages.reopened', { name: result.unit.name }), warnings: result.warnings },
            result.unit,
          ),
      },
    )
  }

  return (
    <Modal
      title={t('org.structure.dialogs.reopenTitle', { name: unitName })}
      description={t('org.structure.dialogs.reopenHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        {unit.effective_to ? (
          <p className="text-sm text-slate-700">
            {t('org.structure.dialogs.closedOn', { date: formatDate(unit.effective_to, language) })}
          </p>
        ) : null}
        <TextAreaField label={t('org.fields.reason')} value={reason} onChange={setReason} maxLength={500} />
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('org.actions.confirmReopen')} />
      </form>
    </Modal>
  )
}
