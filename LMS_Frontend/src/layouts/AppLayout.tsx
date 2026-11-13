import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router'

import { BrandMark } from '../components/BrandMark'
import { ConnectivityIndicator } from '../components/ConnectivityIndicator'
import { LanguageSelector } from '../components/LanguageSelector'
import { UserMenu } from '../features/auth/UserMenu'
import { SidebarNav } from './SidebarNav'

/**
 * Responsive application shell.
 * - Phones/tablets: header with menu button; navigation opens as a drawer.
 * - Laptops/desktops (lg+): persistent sidebar.
 */
export function AppLayout() {
  const { t } = useTranslation()
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    if (!drawerOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [drawerOpen])

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main-content"
        className="sr-only z-50 rounded bg-white px-3 py-2 text-sm font-medium text-brand-700 focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t('app.skipToContent')}
      </a>

      <header className="sticky top-0 z-30 bg-brand-700 shadow-sm">
        <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label={t('nav.open')}
            aria-expanded={drawerOpen}
            aria-controls="mobile-navigation"
            className="-ml-1 rounded-md p-2 text-white hover:bg-white/10 focus:ring-2 focus:ring-ember-400 focus:outline-none lg:hidden"
          >
            <Menu aria-hidden="true" className="size-5" />
          </button>
          <BrandMark compactOnMobile />
          <div className="ml-auto flex items-center gap-2 sm:gap-4">
            <ConnectivityIndicator />
            <LanguageSelector />
            <UserMenu />
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block">
          <SidebarNav />
        </aside>

        {drawerOpen ? (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              aria-hidden="true"
              className="absolute inset-0 bg-slate-900/50"
              onClick={() => setDrawerOpen(false)}
            />
            <div
              id="mobile-navigation"
              role="dialog"
              aria-modal="true"
              aria-label={t('nav.label')}
              className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-xl"
            >
              <div className="flex h-16 items-center justify-between gap-3 border-b border-slate-200 pr-3 pl-4">
                <BrandMark tone="onLight" />
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  aria-label={t('nav.close')}
                  className="rounded-md p-2 text-slate-600 hover:bg-slate-100 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                >
                  <X aria-hidden="true" className="size-5" />
                </button>
              </div>
              <div className="overflow-y-auto">
                <SidebarNav onNavigate={() => setDrawerOpen(false)} />
              </div>
            </div>
          </div>
        ) : null}

        <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 focus:outline-none">
          <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
