import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { BrandMark } from '../components/BrandMark'
import { ConnectivityIndicator } from '../components/ConnectivityIndicator'
import { LanguageSelector } from '../components/LanguageSelector'

/**
 * Branded frame for the sign-in and change-password pages.
 * - Phones/tablets: navy band (brand, connection status, language) above the form.
 * - Laptops/desktops (lg+): navy brand panel on the left, form on the right.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-dvh flex-col bg-slate-50 lg:flex-row">
      <a
        href="#main-content"
        className="sr-only z-50 rounded bg-white px-3 py-2 text-sm font-medium text-brand-700 focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t('app.skipToContent')}
      </a>
      <header className="relative overflow-hidden bg-brand-800 text-white lg:flex lg:w-5/12 lg:max-w-xl lg:flex-col">
        <div className="relative z-10 flex min-h-16 flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-10 lg:pt-10">
          <BrandMark compactOnMobile />
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <ConnectivityIndicator />
            <LanguageSelector />
          </div>
        </div>

        <div className="relative z-10 hidden flex-1 flex-col justify-center px-10 pb-20 lg:flex">
          <span aria-hidden="true" className="mb-6 block h-1 w-16 rounded-full bg-gold-400" />
          <p className="max-w-sm text-3xl leading-tight font-semibold">{t('auth.brand.headline')}</p>
          <p className="mt-4 max-w-sm text-base text-white/80">{t('auth.brand.tagline')}</p>
        </div>

        <svg
          aria-hidden="true"
          viewBox="0 0 32 32"
          className="pointer-events-none absolute -right-28 -bottom-28 hidden size-112 opacity-10 lg:block"
        >
          <path d="M20.5 6.5a10 10 0 1 0 0 19 8 8 0 1 1 0-19z" className="fill-gold-300" />
        </svg>
        <div
          aria-hidden="true"
          className="absolute inset-x-0 bottom-0 h-1 bg-linear-to-r from-gold-400 via-ember-400 to-gold-400 lg:hidden"
        />
      </header>

      <main
        id="main-content"
        tabIndex={-1}
        className="flex flex-1 items-start justify-center px-4 py-8 focus:outline-none sm:px-6 lg:items-center lg:py-12"
      >
        <div className="w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-lg ring-1 ring-slate-200">
          <div
            aria-hidden="true"
            className="h-1.5 bg-linear-to-r from-brand-700 via-gold-400 to-ember-500"
          />
          <div className="p-6 sm:p-8">{children}</div>
        </div>
      </main>
    </div>
  )
}
