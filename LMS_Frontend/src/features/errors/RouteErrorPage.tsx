import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouteError } from 'react-router'

import { ErrorState } from '../../components/ErrorState'

/** Rendered by the router when a route throws while rendering or loading. */
export function RouteErrorPage() {
  const { t } = useTranslation()
  const error = useRouteError()

  useEffect(() => {
    // Details stay in the developer console; users see a safe message.
    console.error('Route error', error)
  }, [error])

  return (
    <div className="mx-auto max-w-lg p-6">
      <ErrorState
        title={t('errors.unexpectedTitle')}
        message={t('errors.unexpectedBody')}
        onRetry={() => window.location.reload()}
      />
    </div>
  )
}
