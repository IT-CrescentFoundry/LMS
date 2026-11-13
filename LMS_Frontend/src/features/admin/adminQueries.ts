import { useInfiniteQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

import { ApiError } from '../../lib/apiClient'
import { adminService } from '../../services/adminService'
import type { AuditFilters, UserFilters } from '../../types/admin'
import { useAuth } from '../auth/authContext'

export const adminQueryKeys = {
  all: ['admin'] as const,
  users: (filters: UserFilters) => [...adminQueryKeys.all, 'users', filters] as const,
  audit: (filters: AuditFilters) => [...adminQueryKeys.all, 'audit', filters] as const,
}

export function useUsers(filters: UserFilters) {
  return useInfiniteQuery({
    queryKey: adminQueryKeys.users(filters),
    queryFn: ({ pageParam, signal }) => adminService.listUsers(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

/**
 * The backend records every audit-log read as an `audit.events.viewed` event,
 * so this query never refetches by itself (no focus/reconnect/mount refetch,
 * no retry) and is discarded when the page closes. Users refresh explicitly.
 *
 * The abort signal is deliberately NOT passed to the request: if it were, an
 * unmount while loading (e.g. React StrictMode's development remount) would
 * cancel the request and the remount would send a second one - and the
 * backend may already have audited the first. Without it, the remount reuses
 * the in-flight request, so one page open is one audited read.
 */
export function useAuditEvents(filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: adminQueryKeys.audit(filters),
    queryFn: ({ pageParam }) => adminService.listAuditEvents(filters, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  })
}

/**
 * A 403 from an admin endpoint means the session's permissions (or its
 * must-change-password state) changed since they were loaded: re-read the
 * session so navigation and route guards catch up with the server.
 */
export function useRefreshSessionOnForbidden(error: unknown) {
  const { refresh } = useAuth()
  useEffect(() => {
    if (error instanceof ApiError && error.status === 403) void refresh()
  }, [error, refresh])
}
