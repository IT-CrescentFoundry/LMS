import { apiRequest, isRecord } from '../lib/apiClient'
import type { CheckStatus, ComponentCheck, LivenessReport, ReadinessReport } from '../types/health'

const CHECK_STATUSES: readonly CheckStatus[] = ['ok', 'not_configured', 'unavailable']

export function parseLiveness(data: unknown): LivenessReport {
  if (
    !isRecord(data) ||
    data.status !== 'ok' ||
    typeof data.service !== 'string' ||
    typeof data.version !== 'string' ||
    typeof data.timestamp !== 'string'
  ) {
    throw new TypeError('Invalid liveness response')
  }
  return {
    status: 'ok',
    service: data.service,
    version: data.version,
    timestamp: data.timestamp,
  }
}

function parseCheck(data: unknown): ComponentCheck {
  if (!isRecord(data) || !CHECK_STATUSES.includes(data.status as CheckStatus)) {
    throw new TypeError('Invalid readiness check')
  }
  return {
    status: data.status as CheckStatus,
    detail: typeof data.detail === 'string' ? data.detail : null,
    duration_ms: typeof data.duration_ms === 'number' ? data.duration_ms : null,
  }
}

export function parseReadiness(data: unknown): ReadinessReport {
  if (
    !isRecord(data) ||
    (data.status !== 'ready' && data.status !== 'not_ready') ||
    !isRecord(data.checks) ||
    typeof data.timestamp !== 'string'
  ) {
    throw new TypeError('Invalid readiness response')
  }
  const checks: Record<string, ComponentCheck> = {}
  for (const [name, check] of Object.entries(data.checks)) {
    checks[name] = parseCheck(check)
  }
  return { status: data.status, checks, timestamp: data.timestamp }
}

export const healthService = {
  getLiveness(signal?: AbortSignal): Promise<LivenessReport> {
    return apiRequest('/health/live', { parse: parseLiveness, signal, timeoutMs: 5_000 })
  },

  /** A 503 is a valid "not ready" report, not an error. */
  getReadiness(signal?: AbortSignal): Promise<ReadinessReport> {
    return apiRequest('/health/ready', {
      parse: parseReadiness,
      signal,
      timeoutMs: 10_000,
      acceptStatuses: [503],
    })
  },
}
