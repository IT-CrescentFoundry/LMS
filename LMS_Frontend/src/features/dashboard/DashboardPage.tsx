import { Award, GraduationCap, Info, Route, Sparkles, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { SystemStatusPanel } from '../system-status/SystemStatusPanel'

type PlannedModuleKey = 'induction' | 'rolePaths' | 'competency' | 'career'

const PLANNED_MODULES: readonly { key: PlannedModuleKey; icon: LucideIcon }[] = [
  { key: 'induction', icon: GraduationCap },
  { key: 'rolePaths', icon: Route },
  { key: 'competency', icon: Award },
  { key: 'career', icon: Sparkles },
]

/** Stage A placeholder dashboard. Shows no learner data: none exists yet. */
export function DashboardPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {t('dashboard.title')}
        </h1>
        <p className="max-w-3xl text-slate-600">{t('dashboard.subtitle')}</p>
      </header>

      <div className="flex gap-3 rounded-lg border border-brand-100 bg-brand-50 p-4 text-brand-900">
        <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-brand-600" />
        <div className="space-y-1">
          <p className="font-medium">{t('dashboard.foundationNotice.title')}</p>
          <p className="text-sm text-brand-800">{t('dashboard.foundationNotice.body')}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section aria-labelledby="planned-modules-heading" className="space-y-4 lg:col-span-2">
          <h2 id="planned-modules-heading" className="text-base font-semibold text-slate-900">
            {t('dashboard.plannedModules.title')}
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {PLANNED_MODULES.map(({ key, icon: Icon }) => (
              <li
                key={key}
                className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <span className="rounded-full bg-ember-400/15 px-2 py-0.5 text-xs font-medium text-ember-600">
                    {t('dashboard.plannedModules.badge')}
                  </span>
                </div>
                <h3 className="font-semibold text-slate-900">
                  {t(`dashboard.plannedModules.${key}.title`)}
                </h3>
                <p className="text-sm text-slate-600">
                  {t(`dashboard.plannedModules.${key}.description`)}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <SystemStatusPanel />
      </div>
    </div>
  )
}
