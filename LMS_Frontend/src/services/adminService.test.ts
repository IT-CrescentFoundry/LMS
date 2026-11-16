import { describe, expect, it } from 'vitest'

import { mockApi, reply } from '../test/renderApp'
import { adminService, parseAuditEvent, parseUserSummary } from './adminService'

const USER = {
  public_id: '01900000-0000-7000-8000-0000000000aa',
  login_id: 'synthetic.user',
  display_name: 'Synthetic User',
  email: null,
  status: 'active',
  roles: ['employee'],
  last_login_at: null,
  created_at: '2026-11-12T10:00:00Z',
  employee: null,
}

const EVENT = {
  event_id: '01900000-0000-7000-8000-0000000000bb',
  occurred_at: '2026-11-12T10:00:00Z',
  event_type: 'auth.login.succeeded',
  outcome: 'success',
  actor: null,
  target_type: 'user_account',
  target_id: '01900000-0000-7000-8000-0000000000aa',
  request_id: 'req-1',
  source_ip: '127.0.0.1',
  user_agent: 'test-agent',
  metadata: { channel: 'web' },
}

describe('admin parsers', () => {
  it('whitelists user summary fields', () => {
    const parsed = parseUserSummary({ ...USER, password_hash: 'secret', version: 3 })
    expect(Object.keys(parsed).sort()).toEqual(Object.keys(USER).sort())
  })

  it('parses audit events with and without an actor', () => {
    expect(parseAuditEvent(EVENT).actor).toBeNull()
    const withActor = parseAuditEvent({
      ...EVENT,
      actor: { public_id: USER.public_id, login_id: 'synthetic.user', display_name: 'Synthetic User', id: 7 },
    })
    expect(withActor.actor).toEqual({
      public_id: USER.public_id,
      login_id: 'synthetic.user',
      display_name: 'Synthetic User',
    })
  })

  it('parses the linked employee (Stage C3) and only its known fields', () => {
    const linked = parseUserSummary({
      ...USER,
      employee: { public_id: 'e-1', employee_code: '00042', full_name: 'Test Person', id: 9 },
    })
    expect(linked.employee).toEqual({ public_id: 'e-1', employee_code: '00042', full_name: 'Test Person' })
    expect(() => parseUserSummary({ ...USER, employee: { public_id: 'e-1' } })).toThrow(TypeError)
  })

  it('rejects malformed items', () => {
    expect(() => parseUserSummary({ ...USER, roles: 'employee' })).toThrow(TypeError)
    expect(() => parseAuditEvent({ ...EVENT, occurred_at: 'yesterday' })).toThrow(TypeError)
  })
})

describe('adminService', () => {
  it('lists users with filters, page size and cursor', async () => {
    const api = mockApi({ 'GET /admin/users': reply({ items: [USER], next_cursor: 'c2' }) })

    const page = await adminService.listUsers({ status: 'active', q: 'synth' }, 'c1')

    expect(page).toEqual({ items: [USER], next_cursor: 'c2' })
    const [request] = api.requestsTo('GET /admin/users')
    expect(Object.fromEntries(request.query)).toEqual({
      status: 'active',
      q: 'synth',
      limit: '25',
      cursor: 'c1',
    })
  })

  it('filters by employee link and accepts a page size (account picker)', async () => {
    const api = mockApi({ 'GET /admin/users': reply({ items: [], next_cursor: null }) })

    await adminService.listUsers({ q: 'ab', linked: false }, null, undefined, 10)
    await adminService.listUsers({ linked: true }, null)

    const [picker, linked] = api.requestsTo('GET /admin/users')
    expect(Object.fromEntries(picker.query)).toEqual({ q: 'ab', linked: 'false', limit: '10' })
    expect(Object.fromEntries(linked.query)).toEqual({ linked: 'true', limit: '25' })
  })

  it('lists audit events and omits empty filters', async () => {
    const api = mockApi({ 'GET /admin/audit-events': reply({ items: [EVENT], next_cursor: null }) })

    await adminService.listAuditEvents(
      { outcome: 'denied', occurred_from: '2026-11-11T18:30:00.000Z' },
      null,
    )

    const [request] = api.requestsTo('GET /admin/audit-events')
    expect(Object.fromEntries(request.query)).toEqual({
      outcome: 'denied',
      occurred_from: '2026-11-11T18:30:00.000Z',
      limit: '50',
    })
  })
})
