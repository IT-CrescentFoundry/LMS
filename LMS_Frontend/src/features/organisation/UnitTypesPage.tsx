import { GitFork, PencilLine, Plus, ShieldAlert, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { primaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { Modal } from '../../components/Modal'
import { organisationService, translationChanges } from '../../services/organisationService'
import { PARENT_RULE_MODES, type ParentRuleMode, type UnitType } from '../../types/organisation'
import { AdminErrorState, Cell, HeaderCell } from '../admin/AdminParts'
import { useRefreshSessionOnForbidden } from '../admin/adminQueries'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from '../admin/tableLayouts'
import { useHasPermission } from '../auth/authContext'
import { PERMISSIONS } from '../auth/permissions'
import { localName } from './names'
import {
  ActiveBadge,
  ChangeError,
  CheckboxField,
  Chip,
  DialogActions,
  NoticeBanner,
  OrgPageHeader,
  RowButton,
  TextAreaField,
  TextField,
  TranslationFields,
  type SuccessNotice,
} from './OrgParts'
import { useOrgMutation, useReloadAndClose as useReload, useUnitTypes } from './orgQueries'

type Dialog = { kind: 'create' } | { kind: 'edit'; type: UnitType } | { kind: 'rules'; type: UnitType }

function ModeBadge({ mode }: { mode: ParentRuleMode }) {
  const { t } = useTranslation()
  return mode === 'strict' ? (
    <Chip tone="ember">
      <ShieldAlert aria-hidden="true" className="mr-1 size-3.5" />
      {t('org.unitTypes.strict')}
    </Chip>
  ) : (
    <Chip tone="slate">
      <TriangleAlert aria-hidden="true" className="mr-1 size-3.5" />
      {t('org.unitTypes.advisory')}
    </Chip>
  )
}

/** Unit type configuration (`/organisation/unit-types`). */
export function UnitTypesPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const canManage = useHasPermission(PERMISSIONS.ORGANISATION_MANAGE)
  const query = useUnitTypes()
  useRefreshSessionOnForbidden(query.error)
  const [dialog, setDialog] = useState<Dialog | null>(null)
  const [notice, setNotice] = useState<SuccessNotice | null>(null)
  const types = query.data ?? []

  const columns = {
    name: t('org.fields.name'),
    code: t('org.fields.code'),
    mode: t('org.unitTypes.columns.mode'),
    parents: t('org.unitTypes.columns.parents'),
    assignment: t('org.unitTypes.columns.assignment'),
    status: t('org.fields.status'),
    actions: t('org.fields.actions'),
  }

  function done(message: string) {
    setDialog(null)
    setNotice({ message, warnings: [] })
  }

  return (
    <div className="space-y-6">
      <OrgPageHeader
        title={t('org.unitTypes.title')}
        subtitle={t('org.unitTypes.subtitle')}
        canManage={canManage}
        actions={
          <button type="button" onClick={() => setDialog({ kind: 'create' })} className={primaryButtonClassName}>
            <Plus aria-hidden="true" className="size-4" />
            {t('org.unitTypes.create')}
          </button>
        }
      />
      {notice ? <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} /> : null}

      <section aria-labelledby="rule-modes" className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-2">
        <h2 id="rule-modes" className="font-semibold text-slate-900 md:col-span-2">
          {t('org.unitTypes.modesTitle')}
        </h2>
        <div className="space-y-1 text-sm">
          <ModeBadge mode="advisory" />
          <p className="text-slate-700">{t('org.unitTypes.advisoryHelp')}</p>
        </div>
        <div className="space-y-1 text-sm">
          <ModeBadge mode="strict" />
          <p className="text-slate-700">{t('org.unitTypes.strictHelp')}</p>
        </div>
        <p className="text-xs text-slate-600 md:col-span-2">{t('org.unitTypes.noRulesHelp')}</p>
      </section>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <AdminErrorState
          title={t('org.unitTypes.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className={TABLE_CONTAINER}>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t('org.unitTypes.caption')}</caption>
            <thead className={TABLE_LAYOUTS.xl.head}>
              <tr>
                {Object.entries(columns)
                  .filter(([key]) => canManage || key !== 'actions')
                  .map(([key, label]) => (
                    <HeaderCell key={key}>{label}</HeaderCell>
                  ))}
              </tr>
            </thead>
            <tbody className={TABLE_LAYOUTS.xl.body}>
              {types.map((type) => (
                <tr key={type.public_id} className={TABLE_LAYOUTS.xl.row}>
                  <Cell layout="xl" label={columns.name}>
                    <span className="font-medium text-slate-900">{localName(type, language)}</span>
                    {type.description ? <span className="block text-xs text-slate-600">{type.description}</span> : null}
                  </Cell>
                  <Cell layout="xl" label={columns.code}>
                    <span className="font-mono">{type.code}</span>
                  </Cell>
                  <Cell layout="xl" label={columns.mode}>
                    <ModeBadge mode={type.parent_rule_mode} />
                  </Cell>
                  <Cell layout="xl" label={columns.parents}>
                    {!type.allow_root && type.allowed_parent_types.length === 0 ? (
                      <span className="text-slate-600">{t('org.unitTypes.noRules')}</span>
                    ) : (
                      <span className="flex flex-wrap gap-1">
                        {type.allow_root ? <Chip>{t('org.unitTypes.topLevel')}</Chip> : null}
                        {type.allowed_parent_types.map((parent) => (
                          <Chip key={parent.public_id}>
                            {localName(types.find((item) => item.public_id === parent.public_id) ?? parent, language)}
                          </Chip>
                        ))}
                      </span>
                    )}
                  </Cell>
                  <Cell layout="xl" label={columns.assignment}>
                    {type.allows_employee_assignment ? t('org.common.yes') : t('org.common.no')}
                  </Cell>
                  <Cell layout="xl" label={columns.status}>
                    <ActiveBadge active={type.is_active} />
                  </Cell>
                  {canManage ? (
                    <Cell layout="xl" label={columns.actions}>
                      <span className="flex flex-wrap gap-2">
                        <RowButton
                          onClick={() => setDialog({ kind: 'edit', type })}
                          label={t('org.actions.editNamed', { name: localName(type, language) })}
                        >
                          <PencilLine aria-hidden="true" className="size-4" />
                          {t('org.actions.edit')}
                        </RowButton>
                        <RowButton
                          onClick={() => setDialog({ kind: 'rules', type })}
                          label={t('org.unitTypes.rulesNamed', { name: localName(type, language) })}
                        >
                          <GitFork aria-hidden="true" className="size-4" />
                          {t('org.unitTypes.rules')}
                        </RowButton>
                      </span>
                    </Cell>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          {types.length === 0 ? <p className="p-6 text-center text-slate-600">{t('org.unitTypes.empty')}</p> : null}
        </div>
      )}

      {dialog?.kind === 'create' || dialog?.kind === 'edit' ? (
        <UnitTypeDialog
          type={dialog.kind === 'edit' ? dialog.type : undefined}
          onClose={() => setDialog(null)}
          onDone={done}
        />
      ) : null}
      {dialog?.kind === 'rules' ? (
        <ParentRulesDialog type={dialog.type} types={types} onClose={() => setDialog(null)} onDone={done} />
      ) : null}
    </div>
  )
}

function UnitTypeDialog({
  type,
  onClose,
  onDone,
}: {
  type?: UnitType
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t } = useTranslation()
  const [code, setCode] = useState(type?.code ?? '')
  const [name, setName] = useState(type?.name ?? '')
  const [description, setDescription] = useState(type?.description ?? '')
  const [sortOrder, setSortOrder] = useState(String(type?.sort_order ?? 0))
  const [assignable, setAssignable] = useState(type?.allows_employee_assignment ?? true)
  const [mode, setMode] = useState<ParentRuleMode>(type?.parent_rule_mode ?? 'advisory')
  const [active, setActive] = useState(type?.is_active ?? true)
  const [translations, setTranslations] = useState<Record<string, string>>({ ...(type?.translations ?? {}) })
  const [showErrors, setShowErrors] = useState(false)
  const reload = useReload(onClose)
  const mutation = useOrgMutation((body: Record<string, unknown>) =>
    type
      ? organisationService.updateUnitType(type.public_id, { ...body, version: type.version })
      : organisationService.createUnitType(body),
  )

  const sort = Number(sortOrder)
  const errors = {
    code: !type && code.trim() === '' ? t('org.errors.required') : undefined,
    name: name.trim() === '' ? t('org.errors.required') : undefined,
    sort: !Number.isInteger(sort) || sort < 0 ? t('org.errors.wholeNumber') : undefined,
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setShowErrors(true)
    if (errors.code || errors.name || errors.sort) return
    const description_ = description.trim() === '' ? null : description.trim()
    let body: Record<string, unknown>
    if (type) {
      body = { version: type.version }
      if (name.trim() !== type.name) body.name = name.trim()
      if (description_ !== type.description) body.description = description_
      if (sort !== type.sort_order) body.sort_order = sort
      if (assignable !== type.allows_employee_assignment) body.allows_employee_assignment = assignable
      if (mode !== type.parent_rule_mode) body.parent_rule_mode = mode
      if (active !== type.is_active) body.is_active = active
      const changes = translationChanges(type.translations, translations)
      if (changes) body.translations = changes
    } else {
      body = {
        code: code.trim(),
        name: name.trim(),
        description: description_,
        sort_order: sort,
        allows_employee_assignment: assignable,
        parent_rule_mode: mode,
        translations: translationChanges({}, translations) ?? {},
      }
    }
    mutation.mutate(body, {
      onSuccess: (result) => onDone(t(type ? 'org.messages.saved' : 'org.messages.created', { name: result.name })),
    })
  }

  return (
    <Modal
      title={type ? t('org.unitTypes.editTitle', { name: type.name }) : t('org.unitTypes.createTitle')}
      onClose={onClose}
      busy={mutation.isPending}
      size="lg"
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {type ? (
            <div className="space-y-1.5">
              <p className="text-sm font-medium text-slate-800">{t('org.fields.code')}</p>
              <p className="font-mono text-sm text-slate-900">{type.code}</p>
              <p className="text-xs text-slate-600">{t('org.unitTypes.codeFixed')}</p>
            </div>
          ) : (
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
          )}
          <TextField
            label={t('org.fields.name')}
            value={name}
            onChange={setName}
            required
            maxLength={150}
            error={showErrors ? errors.name : undefined}
            autoFocus={Boolean(type)}
          />
          <TextField
            label={t('org.fields.sortOrder')}
            type="number"
            inputMode="numeric"
            value={sortOrder}
            onChange={setSortOrder}
            required
            error={showErrors ? errors.sort : undefined}
          />
        </div>
        <TextAreaField label={t('org.fields.description')} value={description} onChange={setDescription} maxLength={500} />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t('org.unitTypes.columns.mode')}</legend>
          {PARENT_RULE_MODES.map((value) => (
            <label key={value} className="flex gap-3 rounded-lg p-2 ring-1 ring-slate-200 has-checked:bg-brand-50 has-checked:ring-brand-300">
              <input
                type="radio"
                name="parent-rule-mode"
                value={value}
                checked={mode === value}
                onChange={() => setMode(value)}
                className="mt-1 size-4 shrink-0 text-brand-700 focus:ring-2 focus:ring-brand-500"
              />
              <span className="text-sm">
                <span className="block font-medium text-slate-900">{t(`org.unitTypes.${value}`)}</span>
                <span className="block text-slate-600">{t(`org.unitTypes.${value}Help`)}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <CheckboxField
          label={t('org.unitTypes.assignmentLabel')}
          checked={assignable}
          onChange={setAssignable}
          hint={t('org.unitTypes.assignmentHint')}
        />
        {type ? (
          <CheckboxField label={t('org.fields.activeLabel')} checked={active} onChange={setActive} hint={t('org.hints.inactive')} />
        ) : null}
        <TranslationFields values={translations} onChange={setTranslations} />
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions
          onCancel={onClose}
          busy={mutation.isPending}
          submitLabel={type ? t('org.actions.save') : t('org.actions.create')}
        />
      </form>
    </Modal>
  )
}

function ParentRulesDialog({
  type,
  types,
  onClose,
  onDone,
}: {
  type: UnitType
  types: readonly UnitType[]
  onClose: () => void
  onDone: (message: string) => void
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage
  const [allowRoot, setAllowRoot] = useState(type.allow_root)
  const [parents, setParents] = useState<ReadonlySet<string>>(
    new Set(type.allowed_parent_types.map((parent) => parent.public_id)),
  )
  const reload = useReload(onClose)
  const mutation = useOrgMutation((body: { version: number; allow_root: boolean; parent_type_ids: string[] }) =>
    organisationService.setParentRules(type.public_id, body),
  )
  const name = localName(type, language)

  function submit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate(
      { version: type.version, allow_root: allowRoot, parent_type_ids: [...parents] },
      { onSuccess: () => onDone(t('org.unitTypes.rulesSaved', { name: type.name })) },
    )
  }

  return (
    <Modal
      title={t('org.unitTypes.rulesTitle', { name })}
      description={t('org.unitTypes.rulesHint')}
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form noValidate onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-700">
          {type.parent_rule_mode === 'strict' ? t('org.unitTypes.strictHelp') : t('org.unitTypes.advisoryHelp')}
        </p>
        <CheckboxField label={t('org.unitTypes.mayBeTopLevel')} checked={allowRoot} onChange={setAllowRoot} />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t('org.unitTypes.allowedParents')}</legend>
          {types.map((candidate) => (
            <CheckboxField
              key={candidate.public_id}
              label={`${localName(candidate, language)} (${candidate.code})${candidate.is_active ? '' : ` — ${t('org.status.inactive')}`}`}
              checked={parents.has(candidate.public_id)}
              onChange={(checked) =>
                setParents((current) => {
                  const next = new Set(current)
                  if (checked) next.add(candidate.public_id)
                  else next.delete(candidate.public_id)
                  return next
                })
              }
            />
          ))}
        </fieldset>
        {!allowRoot && parents.size === 0 ? (
          <p role="status" className="text-sm text-slate-700">
            {t('org.unitTypes.noRulesHelp')}
          </p>
        ) : null}
        {mutation.isError ? <ChangeError error={mutation.error} onReload={reload} /> : null}
        <DialogActions onCancel={onClose} busy={mutation.isPending} submitLabel={t('org.actions.save')} />
      </form>
    </Modal>
  )
}
