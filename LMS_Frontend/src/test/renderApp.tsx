/**
 * Test helpers: render the real application (routes, providers, services) with
 * a stubbed `fetch`. All fixture data is synthetic - never real employee data.
 */

import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { StrictMode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import { AppProviders } from '../app/providers/AppProviders'
import { routes } from '../app/router/routes'
import { PERMISSIONS } from '../features/auth/permissions'

/**
 * Renders the full application at the given path with an isolated cache.
 * `strict` wraps it in React StrictMode, as `main.tsx` does in development
 * (components mount, unmount and mount again).
 */
export function renderApp(path = '/', { strict = false }: { strict?: boolean } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const app = (
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>
  )
  const result = render(strict ? <StrictMode>{app}</StrictMode> : app)
  return { ...result, router, queryClient }
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'test-request-id' },
  })
}

// ------------------------------------------------------------------ health

export const LIVE_OK = {
  status: 'ok',
  service: 'crescent-lms-api',
  version: '0.1.0',
  timestamp: '2026-11-12T10:00:00+00:00',
}

export const READY_OK = {
  status: 'ready',
  checks: { database: { status: 'ok', detail: null, duration_ms: 2.1 } },
  timestamp: '2026-11-12T10:00:00+00:00',
}

export const READY_NO_DATABASE = {
  status: 'not_ready',
  checks: {
    database: {
      status: 'not_configured',
      detail: 'The LMS database connection has not been configured.',
      duration_ms: null,
    },
  },
  timestamp: '2026-11-12T10:00:00+00:00',
}

// ------------------------------------------------------------- identities

export interface UserBody {
  public_id: string
  login_id: string
  display_name: string
  email: string | null
  status: string
  password_must_change: boolean
  roles: string[]
  permissions: string[]
}

const EMPLOYEE_PERMISSIONS = [
  PERMISSIONS.LEARNING_OWN_VIEW,
  PERMISSIONS.CERTIFICATES_OWN_VIEW,
  PERMISSIONS.TRAINING_REQUESTS_SUBMIT,
]

const HR_ADMIN_PERMISSIONS = [
  ...EMPLOYEE_PERMISSIONS,
  PERMISSIONS.TEAM_LEARNING_VIEW,
  PERMISSIONS.LEARNING_CONTENT_MANAGE,
  PERMISSIONS.LEARNING_CONTENT_REVIEW,
  PERMISSIONS.LEARNING_CONTENT_PUBLISH,
  PERMISSIONS.TRAINING_EVENTS_MANAGE,
  PERMISSIONS.USER_ACCOUNTS_VIEW,
  PERMISSIONS.USER_ACCOUNTS_MANAGE,
  PERMISSIONS.USER_SESSIONS_REVOKE,
  PERMISSIONS.USER_ROLES_ASSIGN,
  PERMISSIONS.ACCESS_ROLES_VIEW,
  PERMISSIONS.AUDIT_VIEW,
]

export function makeUser(overrides: Partial<UserBody> = {}): UserBody {
  return {
    public_id: '01900000-0000-7000-8000-000000000001',
    login_id: 'test.employee',
    display_name: 'Test Employee',
    email: null,
    status: 'active',
    password_must_change: false,
    roles: ['employee'],
    permissions: [...EMPLOYEE_PERMISSIONS],
    ...overrides,
  }
}

export const EMPLOYEE = makeUser()

export const HR_ADMIN = makeUser({
  public_id: '01900000-0000-7000-8000-000000000002',
  login_id: 'test.hradmin',
  display_name: 'Test HR Admin',
  roles: ['hr_admin'],
  permissions: [...HR_ADMIN_PERMISSIONS],
})

export const SUPER_ADMIN = makeUser({
  public_id: '01900000-0000-7000-8000-000000000003',
  login_id: 'test.superadmin',
  display_name: 'Test Super Admin',
  roles: ['super_admin'],
  permissions: Object.values(PERMISSIONS),
})

export const ANONYMOUS_SESSION = {
  authenticated: false,
  user: null,
  csrf_token: null,
  idle_expires_at: null,
  absolute_expires_at: null,
}

export function sessionBody(
  user: UserBody,
  { csrfToken = 'csrf-test-token-1', idleMs = 30 * 60_000 }: { csrfToken?: string; idleMs?: number } = {},
) {
  const now = Date.now()
  return {
    authenticated: true,
    user,
    csrf_token: csrfToken,
    idle_expires_at: new Date(now + idleMs).toISOString(),
    absolute_expires_at: new Date(now + 12 * 3_600_000).toISOString(),
  }
}

export function errorBody(code: string, message = 'Error', details?: unknown[]) {
  return { error: { code, message, request_id: 'req-test-1', ...(details ? { details } : {}) } }
}

// ---------------------------------------------------------------- fetch mock

export interface RecordedRequest {
  method: string
  /** Path below the API prefix, without the query string (e.g. "/auth/login"). */
  path: string
  query: URLSearchParams
  headers: Record<string, string>
  body: unknown
}

export interface MockReply {
  status?: number
  body?: unknown
}

export type MockRoute =
  | MockReply
  | Error
  | ((request: RecordedRequest) => MockReply | Error | Promise<MockReply | Error>)

export function reply(body: unknown, status = 200): MockReply {
  return { body, status }
}

const DEFAULT_ROUTES: Record<string, MockRoute> = {
  'GET /health/live': reply(LIVE_OK),
  'GET /health/ready': reply(READY_OK),
  'GET /auth/session': reply(ANONYMOUS_SESSION),
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  const result: Record<string, string> = {}
  new Headers(headers).forEach((value, key) => {
    result[key] = value
  })
  return result
}

/**
 * Stubs `fetch` with a route table keyed by "METHOD /path" (path below
 * /api/v1). Health checks succeed and the session is anonymous unless
 * overridden. Unknown routes answer 404. Every request is recorded.
 */
export function mockApi(routes: Record<string, MockRoute> = {}) {
  const table: Record<string, MockRoute> = { ...DEFAULT_ROUTES, ...routes }
  const requests: RecordedRequest[] = []

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const request: RecordedRequest = {
      method: (init?.method ?? 'GET').toUpperCase(),
      path: url.pathname.replace(/^\/api\/v1/, ''),
      query: url.searchParams,
      headers: headersToRecord(init?.headers),
      body: typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined,
    }
    requests.push(request)

    const route = table[`${request.method} ${request.path}`]
    if (route === undefined) {
      return jsonResponse(errorBody('not_found', 'Not Found'), 404)
    }
    const outcome = typeof route === 'function' ? await route(request) : route
    if (outcome instanceof Error) throw outcome
    const status = outcome.status ?? 200
    if (status === 204) return new Response(null, { status: 204 })
    return jsonResponse(outcome.body, status)
  })
  vi.stubGlobal('fetch', fetchMock)

  return {
    fetchMock,
    requests,
    /** Replaces one route for the rest of the test. */
    setRoute(key: string, route: MockRoute) {
      table[key] = route
    },
    /** Requests matching "METHOD /path". */
    requestsTo(key: string) {
      return requests.filter((request) => `${request.method} ${request.path}` === key)
    },
  }
}

/** Mocks the API with a signed-in session for `user`. */
export function mockSignedIn(user: UserBody, routes: Record<string, MockRoute> = {}) {
  return mockApi({ 'GET /auth/session': reply(sessionBody(user)), ...routes })
}
