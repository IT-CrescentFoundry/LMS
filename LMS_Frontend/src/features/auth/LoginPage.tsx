import { Info, LoaderCircle, LogIn, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { inputClassName, labelClassName, primaryButtonClassName } from '../../components/formStyles'
import { describeApiError, type DescribedError } from './authErrors'
import { useAuth } from './authContext'
import { PasswordField } from './PasswordField'

/**
 * Sign-in with login ID and password (`POST /auth/login`).
 * On success the session is stored by AuthProvider and PublicOnlyRoute
 * continues to the page the user originally asked for.
 */
export function LoginPage() {
  const { t } = useTranslation()
  const { signIn, signedOutReason } = useAuth()
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [missing, setMissing] = useState({ loginId: false, password: false })
  const [failure, setFailure] = useState<DescribedError | null>(null)
  const [pending, setPending] = useState(false)
  const loginIdRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const alertRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (failure) alertRef.current?.focus()
  }, [failure])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const trimmedLoginId = loginId.trim()
    const nextMissing = { loginId: trimmedLoginId === '', password: password === '' }
    setMissing(nextMissing)
    setFailure(null)
    if (nextMissing.loginId) {
      loginIdRef.current?.focus()
      return
    }
    if (nextMissing.password) {
      passwordRef.current?.focus()
      return
    }

    setPending(true)
    try {
      await signIn(trimmedLoginId, password)
    } catch (error) {
      setPassword('')
      setFailure(describeApiError(error))
      setPending(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900">{t('auth.login.title')}</h1>
        <p className="text-sm text-slate-600">{t('auth.login.subtitle')}</p>
      </div>

      {failure ? (
        <div
          ref={alertRef}
          tabIndex={-1}
          role="alert"
          className="flex gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 focus:outline-none"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-red-600" />
          <div className="space-y-1">
            <p className="font-semibold">{t('auth.errors.title')}</p>
            <p>{t(failure.key)}</p>
            {failure.requestId ? (
              <p className="text-xs text-red-800">
                {t('auth.errors.reference', { requestId: failure.requestId })}
              </p>
            ) : null}
          </div>
        </div>
      ) : signedOutReason ? (
        <div
          role="status"
          className={`flex gap-3 rounded-md border p-3 text-sm ${
            signedOutReason === 'expired'
              ? 'border-amber-200 bg-amber-50 text-amber-900'
              : 'border-brand-100 bg-brand-50 text-brand-900'
          }`}
        >
          <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p>
            {signedOutReason === 'expired'
              ? t('auth.login.sessionExpired')
              : t('auth.login.signedOut')}
          </p>
        </div>
      ) : null}

      <form noValidate onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
        <div className="space-y-1.5">
          <label htmlFor="login-id" className={labelClassName}>
            {t('auth.login.loginId')}
          </label>
          <input
            ref={loginIdRef}
            id="login-id"
            name="username"
            type="text"
            value={loginId}
            onChange={(event) => setLoginId(event.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            required
            maxLength={128}
            aria-invalid={missing.loginId ? true : undefined}
            aria-describedby={missing.loginId ? 'login-id-error' : undefined}
            className={inputClassName(missing.loginId)}
          />
          {missing.loginId ? (
            <p id="login-id-error" className="text-sm text-red-700">
              {t('auth.login.loginIdRequired')}
            </p>
          ) : null}
        </div>

        <PasswordField
          id="password"
          label={t('auth.login.password')}
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          error={missing.password ? t('auth.login.passwordRequired') : undefined}
          inputRef={passwordRef}
        />

        <button type="submit" disabled={pending} className={`${primaryButtonClassName} w-full`}>
          {pending ? (
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
          ) : (
            <LogIn aria-hidden="true" className="size-4" />
          )}
          {pending ? t('auth.login.submitting') : t('auth.login.submit')}
        </button>
      </form>

      <p className="border-t border-slate-100 pt-4 text-sm text-slate-600">{t('auth.login.help')}</p>
    </div>
  )
}
