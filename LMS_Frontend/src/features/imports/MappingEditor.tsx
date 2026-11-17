import { LoaderCircle, Plus, ShieldCheck, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { inputClassName, primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { importService } from '../../services/importService'
import type { ImportJob, ImportProfile, MappingSection } from '../../types/imports'
import { InfoNote, SelectField } from '../organisation/OrgParts'
import { ActionError } from './ImportParts'
import { useFieldLabel, useSectionLabel } from './importLabels'
import { useJobMutation } from './importQueries'
import { hasProblems, newSection, retarget, sectionProblems } from './mapping'

/**
 * Column mapping: which worksheet holds which section of the profile, and which
 * column holds which field. Suggestions are exact header matches only. Excluded
 * (sensitive) columns are shown, labelled and never offered. Saving sends the
 * mapping to the server, which checks it again and discards any earlier
 * validation of the job.
 */
export function MappingEditor({
  job,
  profile,
  canEdit,
  onReload,
  onDirtyChange,
}: {
  job: ImportJob
  profile: ImportProfile
  canEdit: boolean
  onReload: () => void
  /** Unsaved edits: the job page holds validation back until they are saved. */
  onDirtyChange?: (dirty: boolean) => void
}) {
  const { t } = useTranslation()
  const sectionLabel = useSectionLabel()
  const fieldLabel = useFieldLabel()
  const initial = job.column_mapping
  const [draft, setDraft] = useState<MappingSection[]>(initial)
  const [dirty, setDirty] = useState(false)
  const save = useJobMutation((sections: MappingSection[]) =>
    importService.setMapping(job.public_id, { version: job.version, sections }),
  )
  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])
  const problems = draft.map((section) => sectionProblems(section, profile, job.workbook))
  const invalid = draft.length === 0 || problems.some(hasProblems)
  const sheetOptions = job.workbook.map((sheet) => ({
    value: sheet.name,
    label: sheet.state === 'visible' ? sheet.name : t('imp.mapping.hiddenSheet', { name: sheet.name }),
  }))
  const kindOptions = profile.sections.map((section) => ({ value: section.kind, label: sectionLabel(section.kind) }))

  function update(index: number, next: MappingSection) {
    setDraft((current) => current.map((item, position) => (position === index ? next : item)))
    setDirty(true)
    save.reset()
  }

  function add() {
    const used = new Set(draft.map((item) => item.section))
    const kind = profile.sections.find((section) => !used.has(section.kind))?.kind
    const section = newSection(profile, job.workbook, kind)
    if (section) {
      setDraft((current) => [...current, section])
      setDirty(true)
    }
  }

  function remove(index: number) {
    setDraft((current) => current.filter((_, position) => position !== index))
    setDirty(true)
  }

  return (
    <section aria-labelledby="imp-mapping" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 id="imp-mapping" className="text-lg font-semibold text-slate-900">
            {t('imp.mapping.title')}
          </h2>
          <p className="max-w-3xl text-sm text-slate-600">
            {job.mapping_confirmed && !dirty ? t('imp.mapping.confirmed') : t('imp.mapping.subtitle')}
          </p>
        </div>
      </div>
      <InfoNote>{t('imp.mapping.exclusionNote')}</InfoNote>

      {draft.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
          {t('imp.mapping.noSections')}
        </p>
      ) : null}

      <ol className="space-y-4">
        {draft.map((section, index) => {
          const sheet = job.workbook.find((item) => item.name === section.sheet)
          const spec = profile.sections.find((item) => item.kind === section.section)
          const issue = problems[index]
          const fieldOptions = (spec?.fields ?? []).map((field) => ({
            value: field.name,
            label: field.required ? t('imp.mapping.requiredField', { field: fieldLabel(field.name) }) : fieldLabel(field.name),
          }))
          return (
            <li
              key={`${index}-${section.sheet}-${section.section}`}
              className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              data-mapping-section={section.section}
            >
              {canEdit ? (
              <div className="flex flex-wrap items-end gap-3">
                <div className="w-full sm:w-56">
                  <SelectField
                    label={t('imp.mapping.section')}
                    value={section.section}
                    options={kindOptions}
                    onChange={(value) => update(index, retarget(section, profile, job.workbook, { section: value }))}
                  />
                </div>
                <div className="w-full sm:w-64">
                  <SelectField
                    label={t('imp.mapping.sheet')}
                    value={section.sheet}
                    options={sheetOptions}
                    onChange={(value) => update(index, retarget(section, profile, job.workbook, { sheet: value }))}
                  />
                </div>
                <p className="text-sm text-slate-600">
                  {sheet?.header_row ? t('imp.mapping.headerRow', { row: sheet.header_row }) : null}
                </p>
                <button
                  type="button"
                  className={`${secondaryButtonClassName} ml-auto`}
                  onClick={() => remove(index)}
                  aria-label={t('imp.mapping.removeFor', { section: sectionLabel(section.section), sheet: section.sheet })}
                >
                  <Trash2 aria-hidden="true" className="size-4" />
                  {t('imp.mapping.remove')}
                </button>
              </div>
              ) : (
                <h3 className="font-semibold break-words text-slate-900">
                  {t('imp.mapping.readOnlyTitle', { section: sectionLabel(section.section), sheet: section.sheet })}{' '}
                  <span className="font-normal text-slate-600">
                    {sheet?.header_row ? t('imp.mapping.headerRow', { row: sheet.header_row }) : null}
                  </span>
                </h3>
              )}

              {issue.noHeader ? (
                <p role="alert" className="text-sm text-red-700">
                  {t('imp.mapping.noHeader')}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <caption className="sr-only">
                      {t('imp.mapping.columnsCaption', { section: sectionLabel(section.section), sheet: section.sheet })}
                    </caption>
                    <thead className="border-b border-slate-200 bg-slate-50">
                      <tr>
                        <th scope="col" className="px-3 py-2 text-xs font-semibold text-slate-600">
                          {t('imp.mapping.column')}
                        </th>
                        <th scope="col" className="px-3 py-2 text-xs font-semibold text-slate-600">
                          {t('imp.mapping.header')}
                        </th>
                        <th scope="col" className="px-3 py-2 text-xs font-semibold text-slate-600">
                          {t('imp.mapping.field')}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(sheet?.headers ?? []).map((header) => {
                        const key = String(header.index)
                        return (
                          <tr key={key} data-column={header.column}>
                            <td className="px-3 py-2 align-top font-mono text-slate-700">{header.column}</td>
                            <td className="px-3 py-2 align-top break-words text-slate-900">{header.text}</td>
                            <td className="min-w-48 px-3 py-2 align-top">
                              {header.excluded ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300">
                                  <ShieldCheck aria-hidden="true" className="size-3.5" />
                                  {t('imp.mapping.excluded')}
                                </span>
                              ) : canEdit ? (
                                <select
                                  aria-label={t('imp.mapping.fieldFor', { header: header.text, column: header.column })}
                                  value={section.columns[key] ?? ''}
                                  className={inputClassName()}
                                  onChange={(event) => {
                                    const columns = { ...section.columns }
                                    if (event.target.value) columns[key] = event.target.value
                                    else delete columns[key]
                                    update(index, { ...section, columns })
                                  }}
                                >
                                  <option value="">{t('imp.mapping.notImported')}</option>
                                  {fieldOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                      {option.label}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <span className="text-slate-700">
                                  {section.columns[key] ? fieldLabel(section.columns[key]) : t('imp.mapping.notImported')}
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              {issue.missing.length > 0 ? (
                <p className="text-sm text-red-700">
                  {t('imp.mapping.missing', { fields: issue.missing.map(fieldLabel).join(', ') })}
                </p>
              ) : null}
              {issue.twice.length > 0 ? (
                <p className="text-sm text-red-700">
                  {t('imp.mapping.twice', { fields: issue.twice.map(fieldLabel).join(', ') })}
                </p>
              ) : null}
            </li>
          )
        })}
      </ol>

      {canEdit ? (
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className={secondaryButtonClassName} onClick={add}>
            <Plus aria-hidden="true" className="size-4" />
            {t('imp.mapping.add')}
          </button>
          <button
            type="button"
            className={primaryButtonClassName}
            disabled={invalid || save.isPending || (job.mapping_confirmed && !dirty)}
            onClick={() => save.mutate(draft, { onSuccess: () => setDirty(false) })}
          >
            {save.isPending ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
            {t('imp.mapping.save')}
          </button>
          {dirty && job.mapping_confirmed ? (
            <p className="text-sm text-amber-800">{t('imp.mapping.unsavedChanges')}</p>
          ) : null}
        </div>
      ) : null}
      {save.isError ? <ActionError error={save.error} onReload={onReload} /> : null}
    </section>
  )
}
