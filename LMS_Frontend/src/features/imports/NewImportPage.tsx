import { Download, FileUp, LoaderCircle } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router'

import { labelClassName, primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { importService, saveDownload } from '../../services/importService'
import { InfoNote } from '../organisation/OrgParts'
import { ActionError, ImportErrorState } from './ImportParts'
import { formatBytes, useSectionLabel } from './importLabels'
import { useImportProfiles, useJobMutation } from './importQueries'

/**
 * New import (`imports.<profile>.run`): choose the profile, optionally download
 * its standard template, and upload one .xlsx workbook. The file goes to the
 * server as-is; the browser never reads its contents. The server inspects it and
 * the job page continues with the column mapping. Nothing is imported yet.
 */
export function NewImportPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const inputId = useId()
  const hintId = useId()
  const sectionLabel = useSectionLabel()
  const profiles = useImportProfiles()
  const [file, setFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<unknown>(null)
  const upload = useJobMutation(({ profile, chosen }: { profile: string; chosen: File }) =>
    importService.upload(profile, chosen),
  )
  const runnable = (profiles.data ?? []).filter((profile) => profile.can_run)
  const [searchParams] = useSearchParams()
  // `?profile=organisation` (e.g. from the organisation structure page) preselects a profile.
  const [profileCode, setProfileCode] = useState(searchParams.get('profile') ?? '')
  const profile = runnable.find((item) => item.code === profileCode) ?? runnable[0]

  function choose(next: File | null) {
    upload.reset()
    setFile(next)
    if (next === null) setClientError(null)
    else if (!next.name.toLowerCase().endsWith('.xlsx')) setClientError(t('imp.newImport.onlyXlsx'))
    else if (next.size === 0) setClientError(t('imp.errors.codes.file_empty'))
    else setClientError(null)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!profile || !file || clientError) return
    upload.mutate(
      { profile: profile.code, chosen: file },
      { onSuccess: (job) => void navigate(`/imports/${job.public_id}`) },
    )
  }

  async function downloadTemplate() {
    if (!profile) return
    setDownloadError(null)
    try {
      saveDownload(await importService.downloadTemplate(profile))
    } catch (error) {
      setDownloadError(error)
    }
  }

  return (
    <div className="space-y-6">
      <header className="min-w-0 space-y-1">
        <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{t('imp.newImport.title')}</h1>
        <p className="max-w-3xl text-slate-600">{t('imp.newImport.subtitle')}</p>
      </header>

      {profiles.isPending ? (
        <LoadingState />
      ) : profiles.isError ? (
        <ImportErrorState
          title={t('imp.newImport.loadError')}
          error={profiles.error}
          onRetry={() => void profiles.refetch()}
          isRetrying={profiles.isFetching}
        />
      ) : !profile ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600">
          {t('imp.newImport.noProfiles')}
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-6" noValidate>
          <fieldset className="space-y-3">
            <legend className="text-lg font-semibold text-slate-900">{t('imp.newImport.profileTitle')}</legend>
            <ul className="grid gap-3 md:grid-cols-2">
              {runnable.map((item) => (
                <li key={item.code} className="min-w-0">
                  <label
                    className={`flex h-full cursor-pointer gap-3 rounded-xl border p-4 shadow-sm ${
                      item.code === profile.code ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600' : 'border-slate-200 bg-white'
                    }`}
                  >
                    <input
                      type="radio"
                      name="profile"
                      value={item.code}
                      checked={item.code === profile.code}
                      onChange={() => setProfileCode(item.code)}
                      className="mt-1 size-4 shrink-0 accent-brand-700"
                    />
                    <span className="min-w-0 space-y-1">
                      <span className="block font-semibold break-words text-slate-900">
                        {item.code === 'employees' || item.code === 'organisation'
                          ? t(`imp.profiles.${item.code}.title`)
                          : t('imp.profiles.unknown', { code: item.code })}{' '}
                        <span className="font-normal text-slate-500">
                          {t('imp.newImport.version', { version: item.version })}
                        </span>
                      </span>
                      <span className="block text-sm break-words text-slate-600">
                        {item.code === 'employees' || item.code === 'organisation'
                          ? t(`imp.profiles.${item.code}.description`)
                          : null}
                      </span>
                      <span className="block text-sm text-slate-600">
                        {t('imp.newImport.sections', {
                          sections: item.sections.map((section) => sectionLabel(section.kind)).join(', '),
                        })}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>

          <section aria-labelledby="imp-template" className="space-y-2">
            <h2 id="imp-template" className="text-lg font-semibold text-slate-900">
              {t('imp.newImport.templateTitle')}
            </h2>
            <p className="max-w-3xl text-sm text-slate-600">{t('imp.newImport.templateHint')}</p>
            <button type="button" className={secondaryButtonClassName} onClick={() => void downloadTemplate()}>
              <Download aria-hidden="true" className="size-4" />
              {t('imp.actions.downloadTemplate')}
            </button>
            {downloadError ? <ActionError error={downloadError} /> : null}
          </section>

          <section aria-labelledby="imp-file" className="space-y-3">
            <h2 id="imp-file" className="text-lg font-semibold text-slate-900">
              {t('imp.newImport.fileTitle')}
            </h2>
            <InfoNote>{t('imp.newImport.privacyNote')}</InfoNote>
            <div className="space-y-1.5">
              <label htmlFor={inputId} className={labelClassName}>
                {t('imp.newImport.fileLabel')}
              </label>
              <input
                id={inputId}
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                aria-describedby={hintId}
                aria-invalid={clientError ? true : undefined}
                onChange={(event) => choose(event.target.files?.[0] ?? null)}
                className="block w-full max-w-full text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:font-medium file:text-brand-800 hover:file:bg-brand-100"
              />
              <p id={hintId} className="text-sm text-slate-600">
                {t('imp.newImport.fileHint')}
              </p>
              {file ? (
                <p className="text-sm break-all text-slate-700" data-chosen-file>
                  {t('imp.newImport.chosen', { name: file.name, size: formatBytes(file.size, i18n.resolvedLanguage) })}
                </p>
              ) : null}
              {clientError ? (
                <p role="alert" className="text-sm text-red-700">
                  {clientError}
                </p>
              ) : null}
            </div>
          </section>

          {upload.isError ? <ActionError error={upload.error} /> : null}
          <button
            type="submit"
            className={primaryButtonClassName}
            disabled={!file || Boolean(clientError) || upload.isPending}
          >
            {upload.isPending ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : (
              <FileUp aria-hidden="true" className="size-4" />
            )}
            {upload.isPending ? t('imp.newImport.uploading') : t('imp.actions.upload')}
          </button>
        </form>
      )}
    </div>
  )
}
