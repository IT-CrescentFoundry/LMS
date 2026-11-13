import { CircleCheck, KeyRound, LoaderCircle, LogOut, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { primaryButtonClassName, secondaryButtonClassName } from '../../components/formStyles'
import { ApiError } from '../../lib/apiClient'
import { isPasswordIssue, type PasswordIssue } from '../../types/auth'
import { describeApiError, type DescribedError } from './authErrors'
import { useAuth } from './authContext'
import { PasswordField } from './PasswordField'

type FieldKey = 'current' | 'new' | 'confirm'
type FieldErrorKey =
  | 'auth.password.currentRequired'
  | 'auth.password.newRequired'
  | 'auth.password.confirmRequired'
  | 'auth.password.mismatch'
  | 'auth.password.invalidCurrent'

/** Policy issues from the backend, de-duplicated; unknown types become "other". */
function policyIssues(error: ApiError): (PasswordIssue | 'other')[] {
  const issues = error.details.map((detail) => (isPasswordIssue(detail.type) ? detail.type : 'other'))
  return [...new Set(issues.length > 0 ? issues : ['other' as const])]
}

/**
 * Change own password (`POST /auth/password`). Used voluntarily from the user
 * menu, and enforced by RequireAuth while `password_must_change` is set.
 * A successful change rotates the session (new cookie and CSRF token) and
 * signs out every other session.
 */
export function ChangePasswordPage() {
  const { t } = useTranslation()
  const { user, changePassword, signOut } = useAuth()
  const forced = user?.password_must_change ?? false

  const [values, setValues] = useState<Record<FieldKey, string>>({ current: '', new: '', confirm: '' })
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, FieldErrorKey>>>({})
  const [issues, setIssues] = useState<(PasswordIssue | 'other')[]>([])
  const [failure, setFailure] = useState<DescribedError | null>(null)
  const [pending, setPending] = useState(false)
  const [succeeded, setSucceeded] = useState(false)
  const [signOutFailed, setSignOutFailed] = useState(false)
  const alertRef = useRef<HTMLDivElement>(null)
  const firstFieldRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (failure || issues.length > 0) alertRef.current?.focus()
  }, [failure, issues])

  const setValue = (key: FieldKey) => (value: string) =>
    setValues((current) => ({ ...current, [key]: value }))

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const errors: Partial<Record<FieldKey, FieldErrorKey>> = {}
    if (values.current === '') errors.current = 'auth.password.currentRequired'
    if (values.new === '') errors.new = 'auth.password.newRequired'
    if (values.confirm === '') errors.confirm = 'auth.password.confirmRequired'
    else if (values.new !== values.confirm) errors.confirm = 'auth.password.mismatch'
    setFieldErrors(errors)
    setIssues([])
    setFailure(null)
    if (Object.keys(errors).length > 0) return

    setPending(true)
    try {
      await changePassword(values.current, values.new)
      setSucceeded(true)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'invalid_current_password') {
        setFieldErrors({ current: 'auth.password.invalidCurrent' })
        firstFieldRef.current?.focus()
      } else if (error instanceof ApiError && error.code === 'password_policy') {
        setIssues(policyIssues(error))
      } else {
        setFailure(describeApiError(error))
      }
    } finally {
      // Never keep passwords in memory longer than needed.
      setValues({ current: '', new: '', confirm: '' })
      setPending(false)
    }
  }

  async function handleSignOut() {
    setSignOutFailed(false)
    try {
      await signOut()
    } catch {
      setSignOutFailed(true)
    }
  }

  if (succeeded) {
    return (
      <div className="space-y-6">
        <div role="status" className="flex gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4">
          <CircleCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-emerald-600" />
          <div className="space-y-1">
            <h1 className="font-semibold text-emerald-900">{t('auth.password.successTitle')}</h1>
            <p className="text-sm text-emerald-900">{t('auth.password.successBody')}</p>
          </div>
        </div>
        <Link to="/" replace className={`${primaryButtonClassName} w-full`}>
          {t('auth.password.continue')}
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
          <KeyRound aria-hidden="true" className="size-6 text-brand-600" />
          {t('auth.password.title')}
        </h1>
        <p className="text-sm text-slate-600">{t('auth.password.subtitle')}</p>
      </div>

      {forced ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {t('auth.password.forcedNotice')}
        </div>
      ) : null}

      {failure || issues.length > 0 ? (
        <div
          ref={alertRef}
          tabIndex={-1}
          role="alert"
          className="flex gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 focus:outline-none"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-red-600" />
          <div className="space-y-1">
            <p className="font-semibold">{t('auth.password.failedTitle')}</p>
            {issues.length > 0 ? (
              <>
                <p>{t('auth.password.policyTitle')}</p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {issues.map((issue) => (
                    <li key={issue}>{t(`auth.password.issues.${issue}`)}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {failure ? <p>{t(failure.key)}</p> : null}
            {failure?.requestId ? (
              <p className="text-xs text-red-800">
                {t('auth.errors.reference', { requestId: failure.requestId })}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <form noValidate onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
        <PasswordField
          id="current-password"
          label={t('auth.password.current')}
          value={values.current}
          onChange={setValue('current')}
          autoComplete="current-password"
          error={fieldErrors.current ? t(fieldErrors.current) : undefined}
          inputRef={firstFieldRef}
        />
        <PasswordField
          id="new-password"
          label={t('auth.password.new')}
          value={values.new}
          onChange={setValue('new')}
          autoComplete="new-password"
          hint={t('auth.password.hint')}
          error={fieldErrors.new ? t(fieldErrors.new) : undefined}
        />
        <PasswordField
          id="confirm-password"
          label={t('auth.password.confirm')}
          value={values.confirm}
          onChange={setValue('confirm')}
          autoComplete="new-password"
          error={fieldErrors.confirm ? t(fieldErrors.confirm) : undefined}
        />

        <button type="submit" disabled={pending} className={`${primaryButtonClassName} w-full`}>
          {pending ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
          {pending ? t('auth.password.submitting') : t('auth.password.submit')}
        </button>
      </form>

      <div className="border-t border-slate-100 pt-4">
        {forced ? (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => void handleSignOut()}
              className={`${secondaryButtonClassName} w-full`}
            >
              <LogOut aria-hidden="true" className="size-4" />
              {t('auth.userMenu.signOut')}
            </button>
            {signOutFailed ? (
              <p role="alert" className="text-sm text-red-700">
                {t('auth.userMenu.signOutFailed')}
              </p>
            ) : null}
          </div>
        ) : (
          <Link to="/" className={`${secondaryButtonClassName} w-full`}>
            {t('auth.password.back')}
          </Link>
        )}
      </div>
    </div>
  )
}
