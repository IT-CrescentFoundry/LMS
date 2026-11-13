import { describe, expect, it, vi } from 'vitest'

import { errorBody, jsonResponse } from '../test/renderApp'
import {
  ApiError,
  apiRequest,
  buildApiUrl,
  buildQuery,
  CSRF_HEADER,
  parseNoContent,
  setAuthHandlers,
  setCsrfToken,
} from './apiClient'

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

function requestInit(fetchMock: ReturnType<typeof vi.fn>, call = 0): RequestInit {
  return (fetchMock.mock.calls[call] as unknown as [string, RequestInit])[1]
}

describe('buildQuery', () => {
  it('omits undefined, null and blank values and encodes the rest', () => {
    expect(buildQuery({ a: undefined, b: null, c: '', d: '  ', e: 'x y', f: 25 })).toBe('?e=x+y&f=25')
    expect(buildQuery({ a: undefined })).toBe('')
  })
})

describe('CSRF token handling', () => {
  it('sends the in-memory token on state-changing methods only', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ name: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('csrf-abc')

    for (const method of ['POST', 'PUT', 'PATCH', 'DELETE'] as const) {
      await apiRequest('/x', { parse: parseName, method })
    }
    await apiRequest('/x', { parse: parseName })

    for (let call = 0; call < 4; call += 1) {
      expect(requestInit(fetchMock, call).headers).toMatchObject({ [CSRF_HEADER]: 'csrf-abc' })
    }
    expect(requestInit(fetchMock, 4).headers).not.toHaveProperty(CSRF_HEADER)
  })

  it('sends no token when none is held, or when the request opts out (login)', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ name: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/x', { parse: parseName, method: 'POST' })
    setCsrfToken('csrf-abc')
    await apiRequest('/auth/login', { parse: parseName, method: 'POST', csrf: false })

    expect(requestInit(fetchMock, 0).headers).not.toHaveProperty(CSRF_HEADER)
    expect(requestInit(fetchMock, 1).headers).not.toHaveProperty(CSRF_HEADER)
  })

  it('keeps the token out of web storage', async () => {
    setCsrfToken('csrf-abc')
    expect(JSON.stringify({ ...window.localStorage })).not.toContain('csrf-abc')
    expect(JSON.stringify({ ...window.sessionStorage })).not.toContain('csrf-abc')
  })

  it('refreshes the session once and retries once after csrf_failed', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(errorBody('csrf_failed'), 403))
      .mockResolvedValueOnce(jsonResponse({ name: 'saved' }))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('stale-token')
    const refreshSession = vi.fn(async () => setCsrfToken('fresh-token'))
    setAuthHandlers({ refreshSession })

    await expect(apiRequest('/x', { parse: parseName, method: 'POST' })).resolves.toEqual({
      name: 'saved',
    })
    expect(refreshSession).toHaveBeenCalledTimes(1)
    expect(requestInit(fetchMock, 0).headers).toMatchObject({ [CSRF_HEADER]: 'stale-token' })
    expect(requestInit(fetchMock, 1).headers).toMatchObject({ [CSRF_HEADER]: 'fresh-token' })
  })

  it('does not loop: a second csrf_failed is returned to the caller', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(errorBody('csrf_failed'), 403))
    vi.stubGlobal('fetch', fetchMock)
    const refreshSession = vi.fn(async () => undefined)
    setAuthHandlers({ refreshSession })

    await expect(apiRequest('/x', { parse: parseName, method: 'POST' })).rejects.toMatchObject({
      status: 403,
      code: 'csrf_failed',
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(refreshSession).toHaveBeenCalledTimes(1)
  })

  it('never retries safe methods or requests that opt out of recovery', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(errorBody('csrf_failed'), 403))
    vi.stubGlobal('fetch', fetchMock)
    const refreshSession = vi.fn(async () => undefined)
    setAuthHandlers({ refreshSession })

    await expect(apiRequest('/x', { parse: parseName })).rejects.toBeInstanceOf(ApiError)
    await expect(
      apiRequest('/x', { parse: parseName, method: 'POST', authRecovery: false }),
    ).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(refreshSession).not.toHaveBeenCalled()
  })
})

describe('session-ended handling', () => {
  it('notifies the auth layer on 401 unauthenticated', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(errorBody('unauthenticated'), 401)))
    const onUnauthenticated = vi.fn()
    setAuthHandlers({ onUnauthenticated })

    await expect(apiRequest('/admin/users', { parse: parseName })).rejects.toMatchObject({
      status: 401,
    })
    expect(onUnauthenticated).toHaveBeenCalledTimes(1)
  })

  it('does not treat other 401 codes (e.g. wrong password) as an ended session', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(errorBody('invalid_credentials'), 401)))
    const onUnauthenticated = vi.fn()
    setAuthHandlers({ onUnauthenticated })

    await expect(apiRequest('/auth/login', { parse: parseName, method: 'POST' })).rejects.toMatchObject(
      { code: 'invalid_credentials' },
    )
    expect(onUnauthenticated).not.toHaveBeenCalled()
  })

  it('unregisters handlers only if they are still the registered ones', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(errorBody('unauthenticated'), 401)))
    const first = vi.fn()
    const second = vi.fn()
    const unregisterFirst = setAuthHandlers({ onUnauthenticated: first })
    setAuthHandlers({ onUnauthenticated: second })
    unregisterFirst()

    await apiRequest('/x', { parse: parseName }).catch(() => undefined)
    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
  })
})

describe('error details and empty responses', () => {
  it('exposes validation issue details from the error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(
          errorBody('password_policy', 'Policy', [
            { location: ['body', 'new_password'], message: 'too_short', type: 'too_short' },
            { not: 'an issue' },
          ]),
          422,
        ),
      ),
    )

    const error = (await apiRequest('/auth/password', { parse: parseName, method: 'POST' }).catch(
      (e: unknown) => e,
    )) as ApiError
    expect(error.details).toEqual([
      { location: ['body', 'new_password'], message: 'too_short', type: 'too_short' },
    ])
  })

  it('accepts 204 No Content', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })))

    await expect(
      apiRequest('/auth/logout', { parse: parseNoContent, method: 'POST' }),
    ).resolves.toBeUndefined()
  })
})
