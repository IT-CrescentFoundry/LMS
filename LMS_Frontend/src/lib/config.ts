/**
 * Runtime configuration derived from build-time environment variables.
 * Values are validated once at start-up so misconfiguration fails loudly.
 */

export interface AppConfig {
  readonly apiBaseUrl: string
  readonly healthPollIntervalMs: number
}

export const DEFAULT_API_BASE_URL = '/api/v1'
export const DEFAULT_HEALTH_POLL_INTERVAL_MS = 30_000
const MIN_HEALTH_POLL_INTERVAL_MS = 5_000

/** Accepts a same-origin path ("/api/v1") or an absolute http(s) URL. */
export function normaliseApiBaseUrl(raw: string | undefined): string {
  const value = (raw ?? '').trim()
  if (value === '') return DEFAULT_API_BASE_URL

  const withoutTrailingSlash = value.replace(/\/+$/, '')
  if (withoutTrailingSlash.startsWith('/') && !withoutTrailingSlash.startsWith('//')) {
    return withoutTrailingSlash
  }
  if (/^https?:\/\/[^/]+/i.test(withoutTrailingSlash)) {
    return withoutTrailingSlash
  }
  throw new Error(
    `Invalid VITE_API_BASE_URL "${value}". Use a path such as "/api/v1" or an http(s) URL.`,
  )
}

export function parsePollInterval(raw: string | undefined): number {
  if (raw === undefined || raw.trim() === '') return DEFAULT_HEALTH_POLL_INTERVAL_MS
  const parsed = Number(raw)
  if (!Number.isInteger(parsed) || parsed < MIN_HEALTH_POLL_INTERVAL_MS) {
    throw new Error(
      `Invalid VITE_HEALTH_POLL_INTERVAL_MS "${raw}". Use an integer of at least ${MIN_HEALTH_POLL_INTERVAL_MS}.`,
    )
  }
  return parsed
}

export const appConfig: AppConfig = Object.freeze({
  apiBaseUrl: normaliseApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
  healthPollIntervalMs: parsePollInterval(import.meta.env.VITE_HEALTH_POLL_INTERVAL_MS),
})
