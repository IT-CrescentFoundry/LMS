import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import { AppProviders } from '../app/providers/AppProviders'
import { routes } from '../app/router/routes'

/** Renders the full application shell at the given path with an isolated cache. */
export function renderApp(path = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const result = render(
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return { ...result, router, queryClient }
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'test-request-id' },
  })
}

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

/**
 * Stubs global fetch so /health/live and /health/ready return the given
 * responses. Pass an Error to simulate a network failure.
 */
export function mockHealthApi(options: {
  live: unknown | Error
  ready?: { body: unknown; status: number }
}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/health/live')) {
      if (options.live instanceof Error) throw options.live
      return jsonResponse(options.live)
    }
    if (url.endsWith('/health/ready') && options.ready) {
      return jsonResponse(options.ready.body, options.ready.status)
    }
    return jsonResponse({ error: { code: 'not_found', message: 'Not found' } }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
