import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '../../lib/apiClient'

/** Client-side cache for server state (TanStack Query). */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Retry transient failures once; never retry client errors (4xx).
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status !== undefined && error.status < 500) {
            return false
          }
          return failureCount < 1
        },
      },
    },
  })
}
