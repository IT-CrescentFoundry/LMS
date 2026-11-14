import { focusManager } from '@tanstack/react-query'
import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { changeLanguage, resources } from '../../i18n'
import {
  EMPLOYEE,
  errorBody,
  HR_ADMIN,
  mockSignedIn,
  renderApp,
  reply,
  sessionBody,
  SUPER_ADMIN,
} from '../../test/renderApp'

function userRow(index: number, overrides: Record<string, unknown> = {}) {
  return {
    public_id: `01900000-0000-7000-8000-${String(index).padStart(12, '0')}`,
    login_id: `synthetic.user${index}`,
    display_name: `Synthetic User ${index}`,
    email: null,
    status: 'active',
    roles: ['employee'],
    last_login_at: null,
    created_at: '2026-11-12T10:00:00Z',
    ...overrides,
  }
}

function auditRow(index: number, overrides: Record<string, unknown> = {}) {
  return {
    event_id: `01900000-0000-7000-9000-${String(index).padStart(12, '0')}`,
    occurred_at: '2026-11-12T10:00:00Z',
    event_type: 'auth.login.succeeded',
    outcome: 'success',
    actor: null,
    target_type: 'user_account',
    target_id: '01900000-0000-7000-8000-000000000001',
    request_id: `req-${index}`,
    source_ip: '127.0.0.1',
    user_agent: 'synthetic-agent',
    metadata: null,
    ...overrides,
  }
}

const page = (items: unknown[], next_cursor: string | null = null) => reply({ items, next_cursor })

/**
 * The audit table once the events have loaded (it is not rendered while the request
 * is pending). Event and outcome labels such as "Sign-in succeeded" also appear as
 * <option>s in the filter form, so assertions about the listed events must be scoped
 * to this table: an unscoped text query would match the filter option alone before
 * the data arrives, and both elements afterwards.
 */
function findAuditTable(name = 'Audit events') {
  return screen.findByRole('table', { name })
}

describe('permission guards', () => {
  it.each(['/admin/users', '/admin/audit-log'])(
    'shows a 403 page for %s without calling the API when the permission is missing',
    async (path) => {
      const api = mockSignedIn(EMPLOYEE)
      renderApp(path)

      expect(
        await screen.findByRole('heading', { name: 'You do not have access to this page' }),
      ).toBeInTheDocument()
      expect(api.requests.some((request) => request.path.startsWith('/admin/'))).toBe(false)
    },
  )

  it('re-reads the session when the API answers 403 (permissions changed meanwhile)', async () => {
    const api = mockSignedIn(HR_ADMIN, { 'GET /admin/users': reply(errorBody('forbidden'), 403) })
    renderApp('/admin/users')

    // The refreshed session no longer carries the permission -> 403 page.
    api.setRoute('GET /auth/session', reply(sessionBody({ ...HR_ADMIN, permissions: [] })))
    expect(
      await screen.findByRole('heading', { name: 'You do not have access to this page' }),
    ).toBeInTheDocument()
    expect(api.requestsTo('GET /auth/session').length).toBeGreaterThanOrEqual(2)
  })
})

describe('Users page', () => {
  it('lists accounts with translated statuses and roles and no management controls', async () => {
    mockSignedIn(HR_ADMIN, {
      'GET /admin/users': page([
        userRow(1, { roles: ['hr_admin', 'employee'], email: 'synthetic1@example.invalid' }),
        userRow(2, { status: 'pending_activation', last_login_at: '2026-11-12T09:30:00Z' }),
      ]),
    })
    renderApp('/admin/users')

    const table = await screen.findByRole('table', { name: 'User accounts' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(2)
    expect(within(rows[0]).getByText('Synthetic User 1')).toBeInTheDocument()
    expect(within(rows[0]).getByText('HR Admin')).toBeInTheDocument()
    expect(within(rows[0]).getByText('synthetic1@example.invalid')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Never')).toBeInTheDocument()
    expect(within(rows[1]).getByText('Pending activation')).toBeInTheDocument()
    expect(within(rows[1]).getByText('—')).toBeInTheDocument()
    expect(screen.getByText('Showing 2 accounts')).toBeInTheDocument()
    expect(screen.getByText('Read only')).toBeInTheDocument()

    const main = screen.getByRole('main')
    const buttons = within(main).getAllByRole('button').map((button) => button.textContent)
    expect(buttons).toEqual(['Apply filters', 'Reset'])
  })

  it('applies filters on submit and pages with the cursor', async () => {
    const api = mockSignedIn(SUPER_ADMIN, {
      'GET /admin/users': (request) =>
        request.query.get('cursor') === 'next-1'
          ? page([userRow(3)])
          : page([userRow(1), userRow(2)], 'next-1'),
    })
    const user = userEvent.setup()
    renderApp('/admin/users')

    await screen.findByText('Synthetic User 1')
    await user.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByText('Synthetic User 3')).toBeInTheDocument()
    expect(screen.getByText('Showing 3 accounts')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()

    await user.type(screen.getByRole('searchbox', { name: 'Search' }), '  synth ')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'suspended')
    expect(api.requestsTo('GET /admin/users')).toHaveLength(2) // typing does not fetch
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => expect(api.requestsTo('GET /admin/users')).toHaveLength(3))
    const last = api.requestsTo('GET /admin/users')[2]
    expect(Object.fromEntries(last.query)).toEqual({ q: 'synth', status: 'suspended', limit: '25' })
  })

  it('shows an empty state and a translated error with a reference', async () => {
    const api = mockSignedIn(HR_ADMIN, { 'GET /admin/users': page([]) })
    const user = userEvent.setup()
    renderApp('/admin/users')

    expect(await screen.findByText('No user accounts match these filters.')).toBeInTheDocument()

    api.setRoute('GET /admin/users', reply(errorBody('internal_error'), 500))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'active')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Could not load user accounts.')
    expect(alert).toHaveTextContent('Reference: req-test-1')
  })
})

describe('Audit log page', () => {
  it('lists events with translated labels, actors and targets', async () => {
    mockSignedIn(SUPER_ADMIN, {
      'GET /admin/audit-events': page([
        auditRow(1, {
          event_type: 'authorization.denied',
          outcome: 'denied',
          actor: {
            public_id: '01900000-0000-7000-8000-000000000002',
            login_id: 'test.hradmin',
            display_name: 'Test HR Admin',
          },
        }),
        auditRow(2, { event_type: 'future.event.type', outcome: 'failure', target_type: null, target_id: null }),
      ]),
    })
    renderApp('/admin/audit-log')

    const table = await screen.findByRole('table', { name: 'Audit events' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('Access denied')).toBeInTheDocument()
    expect(within(rows[0]).getByText('authorization.denied')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Denied')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Test HR Admin')).toBeInTheDocument()
    expect(within(rows[0]).getByText('User account')).toBeInTheDocument()
    expect(within(rows[1]).getByText('future.event.type')).toBeInTheDocument()
    expect(within(rows[1]).getByText('No signed-in user')).toBeInTheDocument()
    expect(within(rows[1]).getByText('Failure')).toBeInTheDocument()
    expect(
      screen.getByText('Viewing the audit log is itself recorded in the audit log.'),
    ).toBeInTheDocument()
  })

  it('shows details with metadata rendered as plain text', async () => {
    mockSignedIn(SUPER_ADMIN, {
      'GET /admin/audit-events': page([
        auditRow(1, { metadata: { channel: 'cli', note: '<img src=x onerror=alert(1)>', filters: { a: 1 } } }),
      ]),
    })
    const user = userEvent.setup()
    renderApp('/admin/audit-log')

    const toggle = await screen.findByRole('button', { name: 'Show details' })
    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('req-1')).toBeInTheDocument()
    expect(screen.getByText('synthetic-agent')).toBeInTheDocument()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(screen.getByText('{"a":1}')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })

  it('fetches once, never on window focus, and again only on Refresh', async () => {
    const api = mockSignedIn(SUPER_ADMIN, { 'GET /admin/audit-events': page([auditRow(1)]) })
    const user = userEvent.setup()
    renderApp('/admin/audit-log')

    expect(within(await findAuditTable()).getByText('Sign-in succeeded')).toBeInTheDocument()
    expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(1)

    await act(async () => {
      focusManager.setFocused(false)
      focusManager.setFocused(true)
    })
    expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(2))
    expect(api.requestsTo('GET /admin/audit-events')[1].query.has('cursor')).toBe(false)
    focusManager.setFocused(undefined)
  })

  it('sends one request per page open even under React StrictMode (each read is audited)', async () => {
    let release: () => void = () => undefined
    const api = mockSignedIn(SUPER_ADMIN, {
      // Hold the response so the StrictMode unmount/remount happens mid-request.
      'GET /admin/audit-events': () =>
        new Promise((resolve) => {
          release = () => resolve(page([auditRow(1)]))
        }),
    })
    renderApp('/admin/audit-log', { strict: true })

    await waitFor(() => expect(api.requestsTo('GET /admin/audit-events').length).toBeGreaterThan(0))
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50))
    })
    await act(async () => release())
    expect(within(await findAuditTable()).getByText('Sign-in succeeded')).toBeInTheDocument()
    expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(1)
  })

  it('sends filters as query parameters, with an exclusive end date', async () => {
    const api = mockSignedIn(SUPER_ADMIN, { 'GET /admin/audit-events': page([auditRow(1)], 'cur-2') })
    const user = userEvent.setup()
    renderApp('/admin/audit-log')
    expect(within(await findAuditTable()).getByText('Sign-in succeeded')).toBeInTheDocument()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Event type' }), 'auth.login.failed')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Outcome' }), 'failure')
    await user.type(screen.getByLabelText('From date'), '2026-11-10')
    await user.type(screen.getByLabelText('To date'), '2026-11-12')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(2))
    const query = Object.fromEntries(api.requestsTo('GET /admin/audit-events')[1].query)
    expect(query).toEqual({
      event_type: 'auth.login.failed',
      outcome: 'failure',
      occurred_from: new Date(2026, 10, 10).toISOString(),
      occurred_to: new Date(2026, 10, 13).toISOString(),
      limit: '50',
    })

    await user.click(await screen.findByRole('button', { name: 'Load more' }))
    await waitFor(() => expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(3))
    expect(api.requestsTo('GET /admin/audit-events')[2].query.get('cursor')).toBe('cur-2')
  })

  it('rejects a reversed date range without calling the API', async () => {
    const api = mockSignedIn(SUPER_ADMIN, { 'GET /admin/audit-events': page([]) })
    const user = userEvent.setup()
    renderApp('/admin/audit-log')
    await screen.findByText('No audit events match these filters.')

    await user.type(screen.getByLabelText('From date'), '2026-11-12')
    await user.type(screen.getByLabelText('To date'), '2026-11-10')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    expect(screen.getByRole('alert')).toHaveTextContent('The start date must be on or before the end date.')
    expect(api.requestsTo('GET /admin/audit-events')).toHaveLength(1)
  })

  it.each(['bn', 'hi', 'gu'] as const)('is fully translated in %s', async (code) => {
    mockSignedIn(SUPER_ADMIN, { 'GET /admin/audit-events': page([auditRow(1)]) })
    await changeLanguage(code)
    renderApp('/admin/audit-log')
    const strings = resources[code].common

    expect(await screen.findByRole('heading', { name: strings.admin.audit.title })).toBeInTheDocument()
    const table = await findAuditTable(strings.admin.audit.caption)
    expect(within(table).getByText(strings.audit.events.loginSucceeded)).toBeInTheDocument()
    expect(within(table).getByText(strings.audit.outcomes.success)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: strings.admin.applyFilters })).toBeInTheDocument()
  })
})
