import { CircleAlert, CircleCheck, Eye, RefreshCw, TriangleAlert, X } from 'lucide-react'
import { useId, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { SUPPORTED_LANGUAGES } from '../../i18n/languages'
import { TRANSLATION_LOCALES, type OrgWarning, type UnitStatus } from '../../types/organisation'
import { describeOrgError, isWarningCode, type Blocker } from './orgErrors'

const BADGE = 'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset'

// ----------------------------------------------------------------- headers

export function OrgPageHeader({
  title,
  subtitle,
  canManage,
  actions,
}: {
  title: string
  subtitle: string
  canManage: boolean
  actions?: ReactNode
}) {
  const { t } = useTranslation()
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl font-bold break-words text-slate-900 sm:text-3xl">{title}</h1>
        <p className="max-w-3xl text-slate-600">{subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {canManage ? actions : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
            <Eye aria-hidden="true" className="size-3.5" />
            {t('admin.readOnly')}
          </span>
        )}
      </div>
    </header>
  )
}

/** Short explanatory note (e.g. "functional roles are not access roles"). */
export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-brand-100 bg-brand-50 p-3 text-sm text-brand-900">{children}</p>
  )
}

// ------------------------------------------------------------------ badges

const UNIT_STATUS_TONE: Record<UnitStatus, string> = {
  active: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  closed: 'bg-slate-100 text-slate-700 ring-slate-300',
  not_started: 'bg-amber-50 text-amber-900 ring-amber-200',
}

export function UnitStatusBadge({ status }: { status: UnitStatus }) {
  const { t } = useTranslation()
  return <span className={`${BADGE} ${UNIT_STATUS_TONE[status]}`}>{t(`org.status.${status}`)}</span>
}

export function ActiveBadge({ active }: { active: boolean }) {
  const { t } = useTranslation()
  return active ? (
    <span className={`${BADGE} bg-emerald-50 text-emerald-800 ring-emerald-200`}>{t('org.status.active')}</span>
  ) : (
    <span className={`${BADGE} bg-slate-100 text-slate-700 ring-slate-300`}>{t('org.status.inactive')}</span>
  )
}

export function Chip({ children, tone = 'brand' }: { children: ReactNode; tone?: 'brand' | 'ember' | 'slate' }) {
  const tones = {
    brand: 'bg-brand-50 text-brand-800 ring-brand-200',
    ember: 'bg-orange-50 text-orange-900 ring-orange-200',
    slate: 'bg-slate-100 text-slate-700 ring-slate-300',
  }
  return <span className={`${BADGE} ${tones[tone]}`}>{children}</span>
}

// ------------------------------------------------------- feedback messages

export interface SuccessNotice {
  message: string
  warnings: OrgWarning[]
}

/** Success feedback (polite live region); advisory warnings are listed with it. */
export function NoticeBanner({ notice, onDismiss }: { notice: SuccessNotice; onDismiss: () => void }) {
  const { t } = useTranslation()
  const hasWarnings = notice.warnings.length > 0
  return (
    <div
      role="status"
      className={`flex gap-3 rounded-lg border p-3 text-sm ${
        hasWarnings ? 'border-amber-200 bg-amber-50 text-amber-950' : 'border-emerald-200 bg-emerald-50 text-emerald-950'
      }`}
    >
      {hasWarnings ? (
        <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-amber-700" />
      ) : (
        <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-emerald-700" />
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-medium break-words">{notice.message}</p>
        {hasWarnings ? <WarningList warnings={notice.warnings} /> : null}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={t('org.actions.dismiss')}
        className="-m-1 self-start rounded p-1 hover:bg-black/5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </div>
  )
}

export function WarningList({ warnings }: { warnings: readonly OrgWarning[] }) {
  const { t } = useTranslation()
  return (
    <ul className="list-disc space-y-0.5 pl-5">
      {warnings.map((warning, index) => (
        <li key={`${warning.code}-${index}`}>
          {isWarningCode(warning.code) ? t(`org.warnings.${warning.code}`) : t('org.warnings.generic')}
        </li>
      ))}
    </ul>
  )
}

/**
 * A rejected change, with its translated reason. Dependants that block a closure
 * are listed. A version conflict offers to reload instead of overwriting.
 */
export function ChangeError({ error, onReload }: { error: unknown; onReload?: () => void }) {
  const { t } = useTranslation()
  const described = describeOrgError(error)
  let message: string
  if (described.kind === 'code') message = t(`org.errors.codes.${described.code}`)
  else if (described.kind === 'network') message = t('auth.errors.network')
  else {
    message = described.requestId
      ? `${t('auth.errors.generic')} ${t('auth.errors.reference', { requestId: described.requestId })}`
      : t('auth.errors.generic')
  }
  const conflict = described.kind === 'code' && described.code === 'version_conflict'
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
      <div className="flex gap-2">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-red-600" />
        <div className="min-w-0 space-y-2">
          <p className="font-medium">{t('org.errors.title')}</p>
          <p className="break-words">{message}</p>
          {described.kind === 'code' && described.blockers.length > 0 ? (
            <div>
              <p className="font-medium">{t('org.errors.blockersTitle')}</p>
              <ul className="list-disc space-y-0.5 pl-5">
                {described.blockers.map((blocker: Blocker, index) => (
                  <li key={`${blocker.type}-${blocker.label}-${index}`} className="break-words">
                    {blocker.type === 'other'
                      ? t('org.errors.blockers.other')
                      : t(`org.errors.blockers.${blocker.type}`, { code: blocker.label })}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {conflict && onReload ? (
            <button
              type="button"
              onClick={onReload}
              className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 font-medium text-red-900 shadow-sm ring-1 ring-red-200 hover:bg-red-100 focus:ring-2 focus:ring-red-500 focus:outline-none"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              {t('org.actions.reload')}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------- form fields

interface FieldShell {
  label: string
  hint?: string
  error?: string
  required?: boolean
}

function FieldFrame({
  id,
  label,
  hint,
  error,
  required,
  children,
}: FieldShell & { id: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClassName}>
        {label}
        {required ? (
          <span className="ml-0.5 text-red-700" aria-hidden="true">
            *
          </span>
        ) : (
          <>
            {' '}
            <span className="font-normal text-slate-500">{t('org.fields.optional')}</span>
          </>
        )}
      </label>
      {children}
      {hint ? (
        <p id={`${id}-hint`} className="text-xs text-slate-600">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  )
}

function describedBy(id: string, hint?: string, error?: string): string | undefined {
  const ids = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean)
  return ids.length > 0 ? ids.join(' ') : undefined
}

export function TextField({
  value,
  onChange,
  type = 'text',
  maxLength,
  autoFocus,
  inputMode,
  placeholder,
  ...shell
}: FieldShell & {
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'date' | 'number'
  maxLength?: number
  autoFocus?: boolean
  inputMode?: 'numeric' | 'text'
  placeholder?: string
}) {
  const id = useId()
  return (
    <FieldFrame id={id} {...shell}>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        maxLength={maxLength}
        required={shell.required}
        aria-required={shell.required || undefined}
        aria-invalid={shell.error ? true : undefined}
        aria-describedby={describedBy(id, shell.hint, shell.error)}
        data-autofocus={autoFocus || undefined}
        inputMode={inputMode}
        placeholder={placeholder}
        autoComplete="off"
        className={inputClassName(Boolean(shell.error))}
      />
    </FieldFrame>
  )
}

export function TextAreaField({
  value,
  onChange,
  maxLength,
  ...shell
}: FieldShell & { value: string; onChange: (value: string) => void; maxLength?: number }) {
  const id = useId()
  return (
    <FieldFrame id={id} {...shell}>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        maxLength={maxLength}
        rows={3}
        aria-invalid={shell.error ? true : undefined}
        aria-describedby={describedBy(id, shell.hint, shell.error)}
        className={inputClassName(Boolean(shell.error))}
      />
    </FieldFrame>
  )
}

export interface SelectOption {
  value: string
  label: string
}

export function SelectField({
  value,
  onChange,
  options,
  emptyLabel,
  size,
  autoFocus,
  ...shell
}: FieldShell & {
  value: string
  onChange: (value: string) => void
  /** Initial focus when the dialog opens (Modal looks for data-autofocus). */
  autoFocus?: boolean
  options: readonly SelectOption[]
  /** Adds a first option with the empty value (e.g. "None"). */
  emptyLabel?: string
  /** Shows the list open (listbox) with this many rows. */
  size?: number
}) {
  const id = useId()
  return (
    <FieldFrame id={id} {...shell}>
      <select
        id={id}
        value={value}
        size={size}
        onChange={(event) => onChange(event.target.value)}
        required={shell.required}
        aria-required={shell.required || undefined}
        aria-invalid={shell.error ? true : undefined}
        aria-describedby={describedBy(id, shell.hint, shell.error)}
        data-autofocus={autoFocus || undefined}
        className={inputClassName(Boolean(shell.error))}
      >
        {emptyLabel !== undefined ? <option value="">{emptyLabel}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldFrame>
  )
}

export function CheckboxField({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  hint?: string
}) {
  const id = useId()
  return (
    <div className="flex gap-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="mt-1 size-4 shrink-0 rounded border-slate-300 text-brand-700 focus:ring-2 focus:ring-brand-500"
      />
      <div className="min-w-0">
        <label htmlFor={id} className="text-sm font-medium text-slate-800">
          {label}
        </label>
        {hint ? (
          <p id={`${id}-hint`} className="text-xs text-slate-600">
            {hint}
          </p>
        ) : null}
      </div>
    </div>
  )
}

/** Optional display names in Bengali, Hindi and Gujarati. */
export function TranslationFields({
  values,
  onChange,
}: {
  values: Record<string, string>
  onChange: (values: Record<string, string>) => void
}) {
  const { t } = useTranslation()
  return (
    <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3">
      <legend className="px-1 text-sm font-medium text-slate-800">{t('org.fields.translations')}</legend>
      <p className="text-xs text-slate-600">{t('org.hints.translations')}</p>
      {TRANSLATION_LOCALES.map((locale) => {
        const language = SUPPORTED_LANGUAGES.find((item) => item.code === locale)
        return (
          <TextField
            key={locale}
            label={t('org.fields.translationFor', { language: language?.nativeName ?? locale })}
            value={values[locale] ?? ''}
            onChange={(value) => onChange({ ...values, [locale]: value })}
            maxLength={200}
          />
        )
      })}
    </fieldset>
  )
}

export function DialogActions({
  onCancel,
  submitLabel,
  busy,
  tone = 'primary',
  cancelLabel,
}: {
  onCancel: () => void
  submitLabel: string
  busy: boolean
  tone?: 'primary' | 'danger'
  /** e.g. "Back" on a confirmation step, where the button returns to the form. */
  cancelLabel?: string
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-4">
      <button type="button" onClick={onCancel} disabled={busy} className={secondaryButtonClassName}>
        {cancelLabel ?? t('org.actions.cancel')}
      </button>
      <button
        type="submit"
        disabled={busy}
        aria-busy={busy || undefined}
        className={
          tone === 'danger'
            ? 'inline-flex items-center justify-center gap-2 rounded-md bg-red-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70'
            : primaryButtonClassName
        }
      >
        {busy ? t('org.actions.saving') : submitLabel}
      </button>
    </div>
  )
}

/** Compact row action button used in tables and panels. */
export function RowButton({
  onClick,
  children,
  label,
}: {
  onClick: () => void
  children: ReactNode
  /** Accessible name when the visible text alone is ambiguous (e.g. "Edit"). */
  label?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50 focus:ring-2 focus:ring-brand-500 focus:outline-none"
    >
      {children}
    </button>
  )
}
