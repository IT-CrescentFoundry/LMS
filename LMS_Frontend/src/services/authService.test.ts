import { describe, expect, it } from 'vitest'

import { CSRF_HEADER, hasCsrfToken } from '../lib/apiClient'
import {
  ANONYMOUS_SESSION,
  errorBody,
  HR_ADMIN,
  mockApi,
  reply,
  sessionBody,
} from '../test/renderApp'
import { authService, parseSessionResponse } from './authService'

describe('parseSessionResponse', () => {
  it('parses an anonymous session', () => {
    expect(parseSessionResponse(ANONYMOUS_SESSION)).toEqual({
      session: { authenticated: false },
      csrfToken: null,
    })
  })

  it('separates the CSRF token from the cached session', () => {
    const parsed = parseSessionResponse(sessionBody(HR_ADMIN, { csrfToken: 'tok-1' }))
    expect(parsed.csrfToken).toBe('tok-1')
    expect(parsed.session).not.toHaveProperty('csrf_token')
    expect(parsed.session.authenticated && parsed.session.user.login_id).toBe('test.hradmin')
  })

  it('drops fields the frontend does not know about (e.g. a hash sent by mistake)', () => {
    const body = sessionBody(HR_ADMIN)
    const parsed = parseSessionResponse({
      ...body,
      token_hash: 'deadbeef',
      user: { ...body.user, password_hash: '$argon2id$v=19$secret' },
    })
    const serialised = JSON.stringify(parsed.session)
    expect(serialised).not.toContain('password_hash')
    expect(serialised).not.toContain('argon2')
    expect(serialised).not.toContain('token_hash')
  })

  it('rejects malformed sessions', () => {
    expect(() => parseSessionResponse({ authenticated: true, user: null })).toThrow(TypeError)
    expect(() =>
      parseSessionResponse({ ...sessionBody(HR_ADMIN), idle_expires_at: 'not a date' }),
    ).toThrow(TypeError)
    expect(() => parseSessionResponse({ ...sessionBody(HR_ADMIN), csrf_token: null })).toThrow(
      TypeError,
    )
    expect(() => parseSessionResponse('nope')).toThrow(TypeError)
  })
})

describe('authService', () => {
  it('login posts exactly login_id and password, without a CSRF header, and stores the token', async () => {
    const api = mockApi({ 'POST /auth/login': reply(sessionBody(HR_ADMIN, { csrfToken: 'tok-login' })) })

    const session = await authService.login('test.hradmin', 'correct horse battery')

    const [request] = api.requestsTo('POST /auth/login')
    expect(request.body).toEqual({ login_id: 'test.hradmin', password: 'correct horse battery' })
    expect(request.headers).not.toHaveProperty(CSRF_HEADER.toLowerCase())
    expect(session.user.display_name).toBe('Test HR Admin')
    expect(hasCsrfToken()).toBe(true)
  })

  it('getSession restores the CSRF token used by the next state-changing request', async () => {
    const api = mockApi({
      'GET /auth/session': reply(sessionBody(HR_ADMIN, { csrfToken: 'tok-restored' })),
      'POST /auth/logout': reply(undefined, 204),
    })

    await authService.getSession()
    await authService.logout()

    const [logout] = api.requestsTo('POST /auth/logout')
    expect(logout.headers[CSRF_HEADER.toLowerCase()]).toBe('tok-restored')
    expect(hasCsrfToken()).toBe(false)
  })

  it('an anonymous session clears any held token', async () => {
    mockApi({ 'POST /auth/login': reply(sessionBody(HR_ADMIN)) })
    await authService.login('test.hradmin', 'x')
    expect(hasCsrfToken()).toBe(true)

    await authService.getSession()
    expect(hasCsrfToken()).toBe(false)
  })

  it('logout treats 401 (session already ended) as signed out', async () => {
    mockApi({
      'GET /auth/session': reply(sessionBody(HR_ADMIN)),
      'POST /auth/logout': reply(errorBody('unauthenticated'), 401),
    })
    await authService.getSession()

    await expect(authService.logout()).resolves.toBeUndefined()
    expect(hasCsrfToken()).toBe(false)
  })

  it('logout keeps the session when the server could not be reached', async () => {
    mockApi({
      'GET /auth/session': reply(sessionBody(HR_ADMIN)),
      'POST /auth/logout': new TypeError('Failed to fetch'),
    })
    await authService.getSession()

    await expect(authService.logout()).rejects.toMatchObject({ kind: 'network' })
    expect(hasCsrfToken()).toBe(true)
  })

  it('changePassword sends both passwords with the CSRF token and rotates it', async () => {
    const api = mockApi({
      'GET /auth/session': reply(sessionBody(HR_ADMIN, { csrfToken: 'tok-old' })),
      'POST /auth/password': reply(sessionBody(HR_ADMIN, { csrfToken: 'tok-new' })),
      'POST /auth/logout': reply(undefined, 204),
    })
    await authService.getSession()

    await authService.changePassword('old secret value', 'new secret value')
    await authService.logout()

    const [change] = api.requestsTo('POST /auth/password')
    expect(change.body).toEqual({
      current_password: 'old secret value',
      new_password: 'new secret value',
    })
    expect(change.headers[CSRF_HEADER.toLowerCase()]).toBe('tok-old')
    expect(api.requestsTo('POST /auth/logout')[0].headers[CSRF_HEADER.toLowerCase()]).toBe('tok-new')
  })
})
