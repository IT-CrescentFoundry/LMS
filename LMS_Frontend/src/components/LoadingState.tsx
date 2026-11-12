import { LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface LoadingStateProps {
  label?: string
}

export function LoadingState({ label }: LoadingStateProps) {
  const { t } = useTranslation()

  return (
    <div role="status" className="flex items-center gap-2 py-4 text-sm text-slate-600">
      <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      <span>{label ?? t('common.loading')}</span>
    </div>
  )
}
