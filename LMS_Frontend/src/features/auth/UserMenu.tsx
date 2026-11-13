import { ChevronDown, KeyRound, LoaderCircle, LogOut } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { RoleChips } from '../../components/Badges'
import { useAuth } from './authContext'
import { CHANGE_PASSWORD_PATH } from './safeRedirect'

function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => Array.from(word)[0] ?? '')
    .join('')
  return letters.toLocaleUpperCase() || '?'
}

const MENU_ITEM =
  'flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-left text-sm font-medium text-slate-700 hover:bg-slate-100 focus:ring-2 focus:ring-brand-500 focus:outline-none disabled:opacity-60'

/** Account disclosure menu in the app header: identity, roles, password, sign out. */
export function UserMenu() {
  const { t } = useTranslation()
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelId = useId()

  useEffect(() => {
    if (!open) return undefined
    const onMouseDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  if (user === null) return null

  async function handleSignOut() {
    setPending(true)
    setFailed(false)
    try {
      await signOut()
    } catch {
      setFailed(true)
      setPending(false)
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={t('auth.userMenu.label', { name: user.display_name })}
        className="flex items-center gap-2 rounded-full p-0.5 text-white hover:bg-white/10 focus:ring-2 focus:ring-gold-400 focus:outline-none sm:rounded-md sm:py-1 sm:pr-2 sm:pl-1"
      >
        <span
          aria-hidden="true"
          className="flex size-9 items-center justify-center rounded-full bg-gold-400 text-sm font-semibold text-brand-900"
        >
          {initials(user.display_name)}
        </span>
        <span className="hidden max-w-40 truncate text-sm font-medium md:inline">
          {user.display_name}
        </span>
        <ChevronDown aria-hidden="true" className="hidden size-4 text-white/80 sm:block" />
      </button>

      {open ? (
        <div
          id={panelId}
          className="absolute right-0 z-40 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-lg bg-white p-4 text-slate-900 shadow-xl ring-1 ring-slate-200"
        >
          <p className="font-semibold break-words">{user.display_name}</p>
          <dl className="mt-3 space-y-3 text-sm">
            <div>
              <dt className="text-xs text-slate-500">{t('auth.userMenu.loginId')}</dt>
              <dd className="font-mono break-all text-slate-800">{user.login_id}</dd>
            </div>
            <div>
              <dt className="mb-1 text-xs text-slate-500">{t('auth.userMenu.roles')}</dt>
              <dd>
                <RoleChips roles={user.roles} />
              </dd>
            </div>
          </dl>
          <div className="mt-4 space-y-1 border-t border-slate-100 pt-3">
            <Link to={CHANGE_PASSWORD_PATH} onClick={() => setOpen(false)} className={MENU_ITEM}>
              <KeyRound aria-hidden="true" className="size-4 text-slate-500" />
              {t('auth.userMenu.changePassword')}
            </Link>
            <button
              type="button"
              onClick={() => void handleSignOut()}
              disabled={pending}
              className={MENU_ITEM}
            >
              {pending ? (
                <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-slate-500" />
              ) : (
                <LogOut aria-hidden="true" className="size-4 text-slate-500" />
              )}
              {pending ? t('auth.userMenu.signingOut') : t('auth.userMenu.signOut')}
            </button>
            {failed ? (
              <p role="alert" className="px-3 pt-1 text-sm text-red-700">
                {t('auth.userMenu.signOutFailed')}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
