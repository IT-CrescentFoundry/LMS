/** Mirrors the backend schemas in LMS_Backend/app/schemas/health.py. */

export interface LivenessReport {
  status: 'ok'
  service: string
  version: string
  timestamp: string
}

export type CheckStatus = 'ok' | 'not_configured' | 'unavailable'

export interface ComponentCheck {
  status: CheckStatus
  detail?: string | null
  duration_ms?: number | null
}

export interface ReadinessReport {
  status: 'ready' | 'not_ready'
  checks: Record<string, ComponentCheck>
  timestamp: string
}
