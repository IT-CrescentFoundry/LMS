import { describe, expect, it, vi } from 'vitest'

import { jsonResponse } from '../test/renderApp'
import { ApiError, apiRequest, buildApiUrl } from './apiClient'

const parseName = (data: unknown): { name: string } => {
  if (typeof data === 'object' && data !== null && 'name' in data && typeof data.name === 'string') {
    return { name: data.name }
  }
  throw new TypeError('bad shape')
}

describe('buildApiUrl', () => {
  it('joins the base URL and path', () => {
    expect(buildApiUrl('/health/live', '/api/v1')).toBe('/api/v1/health/live')
    expect(buildApiUrl('health/live', 'http://localhost:8000/api/v1')).toBe(
      'http://localhost:8000/api/v1/health/live',
    )
  })
})

describe('apiRequest', () => {
  it('returns parsed data on success and sends same-origin JSON requests', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ name: 'Induction' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest('/things/1', { parse: parseName, baseUrl: '/api/v1' })).resolves.toEqual(
      { name: 'Induction' },
    )

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v1/things/1')
    expect(init.credentials).toBe('same-origin')
    expect(init.headers).toMatchObject({ Accept: 'application/json' })
  })

  it('serialises a JSON body', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ name: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/things', { parse: parseName, method: 'POST', body: { name: 'x' } })

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.method).toBe('POST')
    expect(init.body).toBe('{"name":"x"}')
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' })
  })

  it('maps the backend error envelope to an ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(
          { error: { code: 'not_found', message: 'Not Found', request_id: 'req-42' } },
          404,
        ),
      ),
    )

    const error = await apiRequest('/missing', { parse: parseName }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      kind: 'http',
      status: 404,
      code: 'not_found',
      requestId: 'req-42',
      message: 'Not Found',
    })
  })

  it('returns the body for explicitly accepted non-2xx statuses', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ name: 'degraded' }, 503)))

    await expect(
      apiRequest('/ready', { parse: parseName, acceptStatuses: [503] }),
    ).resolves.toEqual({ name: 'degraded' })
  })

  it('reports network failures', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))

    await expect(apiRequest('/x', { parse: parseName })).rejects.toMatchObject({
      kind: 'network',
    })
  })

  it('reports unexpected response shapes', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ unexpected: true })))

    await expect(apiRequest('/x', { parse: parseName })).rejects.toMatchObject({
      kind: 'invalid_response',
    })
  })

  it('reports non-JSON error bodies with a generic message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>Bad gateway</html>', { status: 502 })))

    await expect(apiRequest('/x', { parse: parseName })).rejects.toMatchObject({
      kind: 'http',
      status: 502,
      message: 'Request failed with status 502',
    })
  })

  it('times out slow requests', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_input: RequestInfo | URL, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            )
          }),
      ),
    )

    await expect(apiRequest('/slow', { parse: parseName, timeoutMs: 20 })).rejects.toMatchObject({
      kind: 'timeout',
    })
  })
})
