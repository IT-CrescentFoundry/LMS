import { useTranslation } from 'react-i18next'

import { BrandMark } from '../../components/BrandMark'
import { ErrorState } from '../../components/ErrorState'
import { LoadingState } from '../../components/LoadingState'

function BrandedLoadingScreen({ label }: { label: string }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-brand-800 px-4">
      <BrandMark />
      <div className="rounded-lg bg-white px-4">
        <LoadingState label={label} />
      </div>
    </div>
  )
}

/** Full-page screens shown while the session is being checked. */
export function SessionLoadingScreen() {
  const { t } = useTranslation()
  return <BrandedLoadingScreen label={t('auth.checkingSession')} />
}

/**
 * The root route's `HydrateFallback`. On the first page load the router waits
 * for the matched lazy route's code before it renders anything; this is shown
 * meanwhile instead of a blank page. It shares the session screen's layout, so
 * the hand-over to that screen does not shift.
 */
export function AppLoadingScreen() {
  const { t } = useTranslation()
  return <BrandedLoadingScreen label={t('common.loading')} />
}

export function SessionUnavailableScreen({
  onRetry,
  isRetrying,
}: {
  onRetry: () => void
  isRetrying: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-brand-800 px-4">
      <BrandMark />
      <div className="w-full max-w-md">
        <ErrorState
          title={t('auth.unavailableTitle')}
          message={t('auth.unavailableBody')}
          onRetry={onRetry}
          isRetrying={isRetrying}
        />
      </div>
    </div>
  )
}
