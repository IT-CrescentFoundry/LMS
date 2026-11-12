import { useTranslation } from 'react-i18next'

interface BrandMarkProps {
  /** `onDark` for the coloured header, `onLight` for white surfaces. */
  tone?: 'onDark' | 'onLight'
  /** Hide the wordmark on phones (logo only); it stays available to screen readers. */
  compactOnMobile?: boolean
}

export function BrandMark({ tone = 'onDark', compactOnMobile = false }: BrandMarkProps) {
  const { t } = useTranslation()
  const titleClass = tone === 'onDark' ? 'text-white' : 'text-slate-900'
  const subtitleClass = tone === 'onDark' ? 'text-white/75' : 'text-slate-500'

  return (
    <div className="flex min-w-0 items-center gap-3">
      <svg aria-hidden="true" viewBox="0 0 32 32" className="size-9 shrink-0">
        <rect width="32" height="32" rx="7" className="fill-brand-900" />
        <path d="M20.5 6.5a10 10 0 1 0 0 19 8 8 0 1 1 0-19z" className="fill-ember-400" />
      </svg>
      <div className={`min-w-0 leading-tight ${compactOnMobile ? 'sr-only sm:not-sr-only' : ''}`}>
        <p className={`truncate text-base font-semibold ${titleClass}`}>{t('app.companyName')}</p>
        <p className={`truncate text-xs ${subtitleClass}`}>{t('app.productName')}</p>
      </div>
    </div>
  )
}
