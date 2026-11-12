/**
 * Typed HTTP client for the LMS API.
 *
 * - Every response is passed through a `parse` function that validates the
 *   JSON at runtime and narrows it to the expected type.
 * - Failures are normalised into `ApiError` so UI code can handle them
 *   uniformly (network, timeout, HTTP status or invalid response).
 * - Requests are same-origin by default (`credentials: 'same-origin'`), ready
 *   for server-side session cookies in a later stage.
 */

import { appConfig } from './config'

export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'invalid_response'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number
  readonly code?: string
  readonly requestId?: string

  constructor(
    kind: ApiErrorKind,
    message: string,
    details: { status?: number; code?: string; requestId?: string; cause?: unknown } = {},
  ) {
    super(message, { cause: details.cause })
    this.name = 'ApiError'
    this.kind = kind
    this.status = details.status
    this.code = details.code
    this.requestId = details.requestId
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
}

export const DEFAULT_TIMEOUT_MS = 15_000

export function buildApiUrl(path: string, baseUrl: string = appConfig.apiBaseUrl): string {
  const normalisedPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${normalisedPath}`
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions<T>): Promise<T> {
  const {
    parse,
    method = 'GET',
    body,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    acceptStatuses = [],
    baseUrl,
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
}

function readErrorEnvelope(data: unknown): ErrorEnvelopeBody | undefined {
  if (!isRecord(data) || !isRecord(data.error)) return undefined
  const { code, message, request_id } = data.error
  return {
    code: typeof code === 'string' ? code : undefined,
    message: typeof message === 'string' ? message : undefined,
    request_id: typeof request_id === 'string' ? request_id : undefined,
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
