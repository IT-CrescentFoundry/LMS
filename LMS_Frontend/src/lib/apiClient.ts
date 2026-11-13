/**
 * Typed HTTP client for the LMS API.
 *
 * - Every response is passed through a `parse` function that validates the
 *   JSON at runtime and narrows it to the expected type.
 * - Failures are normalised into `ApiError` so UI code can handle them
 *   uniformly (network, timeout, HTTP status or invalid response).
 * - Requests are same-origin (`credentials: 'same-origin'`): the browser sends
 *   the HttpOnly session cookie automatically. JavaScript never sees it.
 *
 * CSRF (matches the backend, see LMS_Backend/app/api/deps.py):
 * - The session-bound CSRF token is returned in the body of the login,
 *   session and password-change responses. It is held ONLY in this module's
 *   memory - never in localStorage, sessionStorage or a cookie - and is sent
 *   in the `X-CSRF-Token` header on state-changing requests.
 * - Login itself needs no token: the backend protects it by checking the
 *   browser-supplied `Origin` header against its trusted origins.
 * - After a page reload the token is restored from `GET /auth/session`.
 *
 * Request and response bodies are never logged.
 */

import { appConfig } from './config'

export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'invalid_response'

/** One entry of the backend's `error.details` list (validation issues). */
export interface ApiErrorDetail {
  location: string[]
  message: string
  type: string
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number
  readonly code?: string
  readonly requestId?: string
  readonly details: readonly ApiErrorDetail[]

  constructor(
    kind: ApiErrorKind,
    message: string,
    details: {
      status?: number
      code?: string
      requestId?: string
      details?: readonly ApiErrorDetail[]
      cause?: unknown
    } = {},
  ) {
    super(message, { cause: details.cause })
    this.name = 'ApiError'
    this.kind = kind
    this.status = details.status
    this.code = details.code
    this.requestId = details.requestId
    this.details = details.details ?? []
  }
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface ApiRequestOptions<T> {
  /** Validates the parsed JSON body and returns it with its proper type. */
  parse: (data: unknown) => T
  method?: HttpMethod
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
  /** Non-2xx statuses whose JSON body is still a valid result (e.g. readiness 503). */
  acceptStatuses?: readonly number[]
  baseUrl?: string
  /** Attach the CSRF token on state-changing methods (default true; false for login). */
  csrf?: boolean
  /**
   * React to session problems (default true): a 401 `unauthenticated` notifies
   * the auth layer, and a 403 `csrf_failed` refreshes the session once and
   * retries the request once.
   */
  authRecovery?: boolean
}

export const DEFAULT_TIMEOUT_MS = 15_000
export const CSRF_HEADER = 'X-CSRF-Token'

const UNSAFE_METHODS: ReadonlySet<HttpMethod> = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

// ---------------------------------------------------------------- session hooks

let csrfToken: string | null = null

/** Stores the session-bound CSRF token in memory (null clears it). */
export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

export function hasCsrfToken(): boolean {
  return csrfToken !== null
}

export interface AuthHandlers {
  /** Called when an authenticated request reports that the session has ended. */
  onUnauthenticated?: () => void
  /** Re-reads the session (and with it the CSRF token). */
  refreshSession?: () => Promise<void>
}

let authHandlers: AuthHandlers = {}

/** Registers the auth layer's handlers; returns a function that unregisters them. */
export function setAuthHandlers(handlers: AuthHandlers | null): () => void {
  const registered = handlers ?? {}
  authHandlers = registered
  return () => {
    if (authHandlers === registered) authHandlers = {}
  }
}

// ---------------------------------------------------------------------- helpers

export function buildApiUrl(path: string, baseUrl: string = appConfig.apiBaseUrl): string {
  const normalisedPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${normalisedPath}`
}

export type QueryValue = string | number | boolean | null | undefined

/** Builds `?a=1&b=x`, omitting undefined, null and blank values. */
export function buildQuery(params: Readonly<Record<string, QueryValue>>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    const text = String(value)
    if (text.trim() === '') continue
    search.append(key, text)
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

/** For endpoints that answer 204 No Content. */
export function parseNoContent(): void {
  return undefined
}

// ---------------------------------------------------------------------- request

export async function apiRequest<T>(path: string, options: ApiRequestOptions<T>): Promise<T> {
  const recover = options.authRecovery ?? true
  const method = options.method ?? 'GET'
  let retried = false

  for (;;) {
    try {
      return await sendOnce(path, options)
    } catch (error) {
      if (!recover || !(error instanceof ApiError) || error.kind !== 'http') throw error

      if (
        error.status === 403 &&
        error.code === 'csrf_failed' &&
        UNSAFE_METHODS.has(method) &&
        !retried &&
        authHandlers.refreshSession
      ) {
        retried = true
        try {
          await authHandlers.refreshSession()
        } catch {
          throw error
        }
        continue
      }

      if (error.status === 401 && error.code === 'unauthenticated') {
        authHandlers.onUnauthenticated?.()
      }
      throw error
    }
  }
}

async function sendOnce<T>(path: string, options: ApiRequestOptions<T>): Promise<T> {
  const {
    parse,
    method = 'GET',
    body,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    acceptStatuses = [],
    baseUrl,
    csrf = true,
  } = options

  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const forwardAbort = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', forwardAbort, { once: true })

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (csrf && UNSAFE_METHODS.has(method) && csrfToken !== null) {
    headers[CSRF_HEADER] = csrfToken
  }

  let response: Response
  try {
    response = await fetch(buildApiUrl(path, baseUrl), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
      signal: controller.signal,
    })
  } catch (error) {
    if (timedOut) {
      throw new ApiError('timeout', `Request timed out after ${timeoutMs} ms`, { cause: error })
    }
    if (signal?.aborted) throw error // caller cancelled; let the caller handle it
    throw new ApiError('network', 'Unable to reach the LMS API', { cause: error })
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', forwardAbort)
  }

  const requestId = response.headers.get('X-Request-ID') ?? undefined
  const data = await readJson(response)

  if (!response.ok && !acceptStatuses.includes(response.status)) {
    const envelope = readErrorEnvelope(data)
    throw new ApiError('http', envelope?.message ?? `Request failed with status ${response.status}`, {
      status: response.status,
      code: envelope?.code,
      requestId: envelope?.request_id ?? requestId,
      details: envelope?.details,
    })
  }

  try {
    return parse(data)
  } catch (error) {
    throw new ApiError('invalid_response', 'The LMS API returned an unexpected response', {
      status: response.status,
      requestId,
      cause: error,
    })
  }
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text === '') return undefined
  try {
    return JSON.parse(text) as unknown
  } catch {
    return undefined
  }
}

interface ErrorEnvelopeBody {
  code?: string
  message?: string
  request_id?: string
  details?: ApiErrorDetail[]
}

function readErrorEnvelope(data: unknown): ErrorEnvelopeBody | undefined {
  if (!isRecord(data) || !isRecord(data.error)) return undefined
  const { code, message, request_id, details } = data.error
  return {
    code: typeof code === 'string' ? code : undefined,
    message: typeof message === 'string' ? message : undefined,
    request_id: typeof request_id === 'string' ? request_id : undefined,
    details: Array.isArray(details) ? details.flatMap(readErrorDetail) : undefined,
  }
}

function readErrorDetail(value: unknown): ApiErrorDetail[] {
  if (!isRecord(value) || typeof value.type !== 'string') return []
  return [
    {
      type: value.type,
      message: typeof value.message === 'string' ? value.message : '',
      location: Array.isArray(value.location)
        ? value.location.filter((part): part is string => typeof part === 'string')
        : [],
    },
  ]
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
