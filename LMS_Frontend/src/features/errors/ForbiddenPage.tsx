import { ShieldAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

export function ForbiddenPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-lg space-y-3 py-12 text-center">
      <ShieldAlert aria-hidden="true" className="mx-auto size-10 text-brand-600" />
      <p className="text-sm font-semibold text-brand-600">403</p>
      <h1 className="text-2xl font-bold text-slate-900">{t('errors.forbiddenTitle')}</h1>
      <p className="text-slate-600">{t('errors.forbiddenBody')}</p>
      <Link
        to="/"
        className="inline-block rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:outline-none"
      >
        {t('errors.backToDashboard')}
      </Link>
    </div>
  )
}
