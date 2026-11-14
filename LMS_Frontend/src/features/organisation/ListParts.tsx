import { LoaderCircle, Search } from 'lucide-react'
import { useId, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'

/**
 * Search box plus "show inactive" switch. With `onSubmit` the search runs on the
 * server when the form is submitted (paginated lists); without it the parent
 * filters the loaded list as the user types.
 */
export function ListToolbar({
  label,
  search,
  onSearch,
  placeholder,
  includeInactive,
  onIncludeInactive,
  inactiveLabel,
  onSubmit,
}: {
  label: string
  search: string
  onSearch: (value: string) => void
  placeholder: string
  includeInactive: boolean
  onIncludeInactive: (value: boolean) => void
  inactiveLabel?: string
  onSubmit?: () => void
}) {
  const { t } = useTranslation()
  const searchId = useId()
  const inactiveId = useId()

  function submit(event: FormEvent) {
    event.preventDefault()
    onSubmit?.()
  }

  return (
    <form
      role="search"
      aria-label={label}
      onSubmit={submit}
      className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="min-w-0 flex-1 space-y-1.5 sm:min-w-64">
        <label htmlFor={searchId} className={labelClassName}>
          {t('org.common.search')}
        </label>
        <input
          id={searchId}
          type="search"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          maxLength={100}
          placeholder={placeholder}
          autoComplete="off"
          className={inputClassName()}
        />
      </div>
      <div className="flex items-center gap-2 pb-2.5">
        <input
          id={inactiveId}
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => onIncludeInactive(event.target.checked)}
          className="size-4 rounded border-slate-300 text-brand-700 focus:ring-2 focus:ring-brand-500"
        />
        <label htmlFor={inactiveId} className="text-sm text-slate-800">
          {inactiveLabel ?? t('org.common.showInactive')}
        </label>
      </div>
      {onSubmit ? (
        <button type="submit" className={primaryButtonClassName}>
          <Search aria-hidden="true" className="size-4" />
          {t('org.common.searchButton')}
        </button>
      ) : null}
    </form>
  )
}

/** "Showing N" status plus a "Load more" button for cursor-paginated lists. */
export function ListFooter({
  countText,
  hasMore,
  loadingMore,
  onLoadMore,
}: {
  countText: string
  hasMore: boolean
  loadingMore: boolean
  onLoadMore: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p role="status" aria-live="polite" className="text-sm text-slate-600">
        {countText}
      </p>
      {hasMore ? (
        <button type="button" onClick={onLoadMore} disabled={loadingMore} className={secondaryButtonClassName}>
          {loadingMore ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : null}
          {t('common.loadMore')}
        </button>
      ) : null}
    </div>
  )
}
