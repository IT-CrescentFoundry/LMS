import { LoaderCircle, RotateCcw, Search } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { AccountStatusBadge, RoleChips } from '../../components/Badges'
import {
  inputClassName,
  labelClassName,
  primaryButtonClassName,
  secondaryButtonClassName,
} from '../../components/formStyles'
import { LoadingState } from '../../components/LoadingState'
import { formatDateTime } from '../../lib/format'
import { ACCOUNT_STATUSES, type AccountStatus, type UserFilters } from '../../types/admin'
import {
  AdminErrorState,
  AdminPageHeader,
  Cell,
  HeaderCell,
} from './AdminParts'
import { TABLE_CONTAINER, TABLE_LAYOUTS } from './tableLayouts'
import { useRefreshSessionOnForbidden, useUsers } from './adminQueries'

/**
 * Read-only directory of user accounts (`GET /admin/users`, permission
 * `user_accounts.view`). Shows only fields the API returns; there are no
 * create, edit, suspend or role-management controls in this stage.
 */
export function UsersPage() {
  const { t, i18n } = useTranslation()
  const searchId = useId()
  const statusId = useId()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<AccountStatus | ''>('')
  const [filters, setFilters] = useState<UserFilters>({})

  const query = useUsers(filters)
  useRefreshSessionOnForbidden(query.error)
  const users = query.data?.pages.flatMap((page) => page.items) ?? []
  const language = i18n.resolvedLanguage

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const q = search.trim()
    const next: UserFilters = {}
    if (q) next.q = q
    if (status) next.status = status
    setFilters(next)
  }

  function resetFilters() {
    setSearch('')
    setStatus('')
    setFilters({})
  }

  const columns = {
    name: t('admin.users.columns.name'),
    loginId: t('admin.users.columns.loginId'),
    email: t('admin.users.columns.email'),
    status: t('admin.users.columns.status'),
    roles: t('admin.users.columns.roles'),
    lastLogin: t('admin.users.columns.lastLogin'),
    created: t('admin.users.columns.created'),
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader title={t('admin.users.title')} subtitle={t('admin.users.subtitle')} />

      <form
        role="search"
        aria-label={t('admin.users.search')}
        onSubmit={applyFilters}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_14rem_auto] lg:items-end"
      >
        <div className="space-y-1.5">
          <label htmlFor={searchId} className={labelClassName}>
            {t('admin.users.search')}
          </label>
          <input
            id={searchId}
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            maxLength={100}
            placeholder={t('admin.users.searchPlaceholder')}
            autoComplete="off"
            className={inputClassName()}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={statusId} className={labelClassName}>
            {t('admin.users.status')}
          </label>
          <select
            id={statusId}
            value={status}
            onChange={(event) => setStatus(event.target.value as AccountStatus | '')}
            className={inputClassName()}
          >
            <option value="">{t('admin.users.allStatuses')}</option>
            {ACCOUNT_STATUSES.map((code) => (
              <option key={code} value={code}>
                {t(`userStatus.${code}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-1">
          <button type="submit" className={primaryButtonClassName}>
            <Search aria-hidden="true" className="size-4" />
            {t('admin.applyFilters')}
          </button>
          <button type="button" onClick={resetFilters} className={secondaryButtonClassName}>
            <RotateCcw aria-hidden="true" className="size-4" />
            {t('admin.resetFilters')}
          </button>
        </div>
      </form>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError && users.length === 0 ? (
        <AdminErrorState
          title={t('admin.users.loadError')}
          error={query.error}
          onRetry={() => void query.refetch()}
          isRetrying={query.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className={TABLE_CONTAINER}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t('admin.users.caption')}</caption>
              <thead className={TABLE_LAYOUTS.md.head}>
                <tr>
                  {Object.values(columns).map((label) => (
                    <HeaderCell key={label}>{label}</HeaderCell>
                  ))}
                </tr>
              </thead>
              <tbody className={TABLE_LAYOUTS.md.body}>
                {users.map((user) => (
                  <tr key={user.public_id} className={TABLE_LAYOUTS.md.row}>
                    <Cell label={columns.name}>
                      <span className="font-medium text-slate-900">{user.display_name}</span>
                    </Cell>
                    <Cell label={columns.loginId}>
                      <span className="font-mono text-slate-800">{user.login_id}</span>
                    </Cell>
                    <Cell label={columns.email}>
                      <span className="break-all text-slate-700">{user.email ?? '—'}</span>
                    </Cell>
                    <Cell label={columns.status}>
                      <AccountStatusBadge status={user.status} />
                    </Cell>
                    <Cell label={columns.roles}>
                      <RoleChips roles={user.roles} />
                    </Cell>
                    <Cell label={columns.lastLogin}>
                      <span className="text-slate-700">
                        {user.last_login_at
                          ? formatDateTime(user.last_login_at, language)
                          : t('common.never')}
                      </span>
                    </Cell>
                    <Cell label={columns.created}>
                      <span className="text-slate-700">
                        {formatDateTime(user.created_at, language, { dateStyle: 'medium' })}
                      </span>
                    </Cell>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 ? (
              <p className="p-6 text-center text-slate-600">{t('admin.users.empty')}</p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p role="status" aria-live="polite" className="text-sm text-slate-600">
              {t('admin.users.count', { count: users.length })}
            </p>
            {query.hasNextPage ? (
              <button
                type="button"
                onClick={() => void query.fetchNextPage()}
                disabled={query.isFetchingNextPage}
                className={secondaryButtonClassName}
              >
                {query.isFetchingNextPage ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : null}
                {t('common.loadMore')}
              </button>
            ) : null}
          </div>

          {query.isFetchNextPageError ? (
            <AdminErrorState
              title={t('admin.users.loadError')}
              error={query.error}
              onRetry={() => void query.fetchNextPage()}
              isRetrying={query.isFetchingNextPage}
            />
          ) : null}
        </div>
      )}
    </div>
  )
}
