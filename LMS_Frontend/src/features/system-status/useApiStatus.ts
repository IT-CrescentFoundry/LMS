import { useQuery } from '@tanstack/react-query'

import { appConfig } from '../../lib/config'
import { healthService } from '../../services/healthService'

export const healthQueryKeys = {
  all: ['health'] as const,
  liveness: () => [...healthQueryKeys.all, 'live'] as const,
  readiness: () => [...healthQueryKeys.all, 'ready'] as const,
}

/**
 * - checking: first check still in progress
 * - online:   API reachable and all readiness checks pass
 * - degraded: API reachable but a dependency (e.g. database) is not ready
 * - offline:  API not reachable
 */
export type ApiConnectionState = 'checking' | 'online' | 'degraded' | 'offline'

export function useApiStatus() {
  const liveness = useQuery({
    queryKey: healthQueryKeys.liveness(),
    queryFn: ({ signal }) => healthService.getLiveness(signal),
    refetchInterval: appConfig.healthPollIntervalMs,
  })

  const readiness = useQuery({
    queryKey: healthQueryKeys.readiness(),
    queryFn: ({ signal }) => healthService.getReadiness(signal),
    enabled: liveness.isSuccess,
    refetchInterval: appConfig.healthPollIntervalMs,
    retry: false,
  })

  let state: ApiConnectionState
  if (liveness.isError) {
    state = 'offline'
  } else if (liveness.isPending) {
    state = 'checking'
  } else if (readiness.data?.status === 'ready') {
    state = 'online'
  } else if (readiness.data || readiness.isError) {
    state = 'degraded'
  } else {
    state = 'checking'
  }

  return {
    state,
    liveness: liveness.data,
    readiness: readiness.data,
    error: liveness.error ?? readiness.error,
    isFetching: liveness.isFetching || readiness.isFetching,
    lastCheckedAt: Math.max(liveness.dataUpdatedAt, liveness.errorUpdatedAt) || undefined,
    refetch: async () => {
      await liveness.refetch()
      await readiness.refetch()
    },
  }
}
