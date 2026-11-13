import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CSRF_HEADER } from '../../lib/apiClient'
import {
  ANONYMOUS_SESSION,
  EMPLOYEE,
  errorBody,
  HR_ADMIN,
  makeUser,
  mockApi,
  mockSignedIn,
  renderApp,
  reply,
  sessionBody,
} from '../../test/renderApp'
import { safeRedirectTarget } from './safeRedirect'

const CSRF = CSRF_HEADER.toLowerCase()
const PASSWORD = 'synthetic-Password-42'

async function fillLogin(user: ReturnType<typeof userEvent.setup>, loginId: string, password: string) {
  await user.type(await screen.findByLabelText('Login ID'), loginId)
  await user.type(screen.getByLabelText('Password'), password)
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('session restoration', () => {
  it('shows the signed-in shell when a session exists', async () => {
    mockSignedIn(HR_ADMIN)
    renderApp()

    expect(
      await screen.findByRole('button', { name: 'Account menu for Test HR Admin' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Welcome to Crescent Foundry LMS')
  })

  it('sends anonymous visitors to the sign-in page', async () => {
    mockApi()
    const { router } = renderApp('/admin/users')

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.state).toEqual({ from: '/admin/users' })
  })

  it('does not treat an unreachable API as signed out', async () => {
    const api = mockApi({ 'GET /auth/session': new TypeError('Failed to fetch') })
    const user = userEvent.setup()
    const { router } = renderApp('/')

    expect(await screen.findByText('Cannot reach the LMS')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/')

    api.setRoute('GET /auth/session', reply(sessionBody(EMPLOYEE)))
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(
      await screen.findByRole('button', { name: 'Account menu for Test Employee' }),
    ).toBeInTheDocument()
  })

  it('uses the CSRF token restored by /auth/session for the next state-changing request', async () => {
    const api = mockApi({
      'GET /auth/session': reply(sessionBody(EMPLOYEE, { csrfToken: 'restored-token' })),
      'POST /auth/logout': reply(undefined, 204),
    })
    const user = userEvent.setup()
    renderApp()

    await user.click(await screen.findByRole('button', { name: 'Account menu for Test Employee' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    await screen.findByRole('heading', { name: 'Sign in' })
    expect(api.requestsTo('POST /auth/logout')[0].headers[CSRF]).toBe('restored-token')
  })
})

describe('sign-in', () => {
  it('renders an accessible, branded form', async () => {
    mockApi()
    renderApp('/login')

    const loginId = await screen.findByLabelText('Login ID')
    expect(loginId).toHaveAttribute('autocomplete', 'username')
    expect(loginId).toHaveAttribute('autocapitalize', 'none')
    const password = screen.getByLabelText('Password')
    expect(password).toHaveAttribute('type', 'password')
    expect(password).toHaveAttribute('autocomplete', 'current-password')
    expect(screen.getByText('Crescent Foundry')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Language' })).toBeInTheDocument()
    expect(screen.getByText(/Contact HR for help/)).toBeInTheDocument()
  })

  it('validates required fields without calling the API', async () => {
    const api = mockApi()
    const user = userEvent.setup()
    renderApp('/login')

    await user.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(screen.getByText('Enter your login ID.')).toBeInTheDocument()
    expect(screen.getByLabelText('Login ID')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Login ID')).toHaveFocus()

    await user.type(screen.getByLabelText('Login ID'), 'test.employee')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toHaveFocus()

    expect(api.requestsTo('POST /auth/login')).toHaveLength(0)
  })

  it('signs in with exactly login_id and password and returns to the requested page', async () => {
    const api = mockApi({
      'POST /auth/login': reply(sessionBody(HR_ADMIN, { csrfToken: 'login-token' })),
      'GET /admin/users': reply({ items: [], next_cursor: null }),
    })
    const user = userEvent.setup()
    const { router } = renderApp('/admin/users')

    await fillLogin(user, '  test.hradmin ', PASSWORD)

    expect(await screen.findByRole('heading', { name: 'User accounts' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/admin/users')
    const [login] = api.requestsTo('POST /auth/login')
    expect(login.body).toEqual({ login_id: 'test.hradmin', password: PASSWORD })
    expect(login.headers).not.toHaveProperty(CSRF)
  })

  it('shows a generic message on wrong credentials, clears the password and focuses the alert', async () => {
    mockApi({ 'POST /auth/login': reply(errorBody('invalid_credentials'), 401) })
    const user = userEvent.setup()
    renderApp('/login')

    await fillLogin(user, 'test.employee', 'wrong-password')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('The login ID or password is incorrect.')
    expect(alert).toHaveFocus()
    expect(screen.getByLabelText('Password')).toHaveValue('')
    expect(screen.getByLabelText('Login ID')).toHaveValue('test.employee')
  })

  it.each([
    ['too_many_attempts', 429, 'Too many unsuccessful attempts'],
    ['account_inactive', 403, 'This account is not active. Please contact HR.'],
    ['origin_not_allowed', 403, 'Sign-in is not allowed from this web address'],
  ])('translates the %s error', async (code, status, text) => {
    mockApi({ 'POST /auth/login': reply(errorBody(code), status) })
    const user = userEvent.setup()
    renderApp('/login')

    await fillLogin(user, 'test.employee', PASSWORD)
    expect(await screen.findByRole('alert')).toHaveTextContent(text)
  })

  it('reports network failures and unexpected errors with a reference', async () => {
    const api = mockApi({ 'POST /auth/login': new TypeError('Failed to fetch') })
    const user = userEvent.setup()
    renderApp('/login')

    await fillLogin(user, 'test.employee', PASSWORD)
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the LMS')

    api.setRoute('POST /auth/login', reply(errorBody('internal_error'), 500))
    await user.type(screen.getByLabelText('Password'), PASSWORD)
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Reference: req-test-1'),
    )
  })

  it('disables the button while signing in', async () => {
    let release: (value: unknown) => void = () => undefined
    mockApi({
      'POST /auth/login': () =>
        new Promise((resolve) => {
          release = () => resolve(reply(sessionBody(EMPLOYEE)))
        }),
    })
    const user = userEvent.setup()
    renderApp('/login')

    await fillLogin(user, 'test.employee', PASSWORD)
    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled()

    await act(async () => release(undefined))
    expect(
      await screen.findByRole('heading', { name: 'Welcome to Crescent Foundry LMS' }),
    ).toBeInTheDocument()
  })

  it('toggles password visibility', async () => {
    mockApi()
    const user = userEvent.setup()
    renderApp('/login')

    const toggle = await screen.findByRole('button', { name: 'Show password' })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
    await user.click(toggle)
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })

  it('sends signed-in users away from the sign-in page', async () => {
    mockSignedIn(EMPLOYEE)
    const { router } = renderApp('/login')

    await screen.findByRole('heading', { name: 'Welcome to Crescent Foundry LMS' })
    expect(router.state.location.pathname).toBe('/')
  })
})

describe('safeRedirectTarget', () => {
  it('only allows internal paths from router state', () => {
    expect(safeRedirectTarget({ from: '/admin/users?x=1' })).toBe('/admin/users?x=1')
    expect(safeRedirectTarget({ from: 'https://evil.example' })).toBe('/')
    expect(safeRedirectTarget({ from: '//evil.example' })).toBe('/')
    expect(safeRedirectTarget({ from: '/\\evil.example' })).toBe('/')
    expect(safeRedirectTarget({ from: '/login?next=1' })).toBe('/')
    expect(safeRedirectTarget({ from: 42 })).toBe('/')
    expect(safeRedirectTarget(null)).toBe('/')
  })
})

describe('sign-out', () => {
  it('revokes the session, purges cached admin data and shows the sign-in page', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /admin/users': reply({
        items: [
          {
            public_id: '01900000-0000-7000-8000-0000000000aa',
            login_id: 'synthetic.user',
            display_name: 'Synthetic User',
            email: null,
            status: 'active',
            roles: ['employee'],
            last_login_at: null,
            created_at: '2026-11-12T10:00:00Z',
          },
        ],
        next_cursor: null,
      }),
      'POST /auth/logout': reply(undefined, 204),
    })
    const user = userEvent.setup()
    const { queryClient, router } = renderApp('/admin/users')

    expect(await screen.findByText('Synthetic User')).toBeInTheDocument()
    expect(queryClient.getQueryCache().findAll({ queryKey: ['admin'] })).not.toHaveLength(0)

    await user.click(screen.getByRole('button', { name: 'Account menu for Test HR Admin' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByText('You have signed out.')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.state).toBeNull()
    expect(api.requestsTo('POST /auth/logout')[0].headers[CSRF]).toBe('csrf-test-token-1')
    expect(queryClient.getQueryCache().findAll({ queryKey: ['admin'] })).toHaveLength(0)
  })

  it('treats 401 on logout as already signed out', async () => {
    mockSignedIn(EMPLOYEE, { 'POST /auth/logout': reply(errorBody('unauthenticated'), 401) })
    const user = userEvent.setup()
    renderApp()

    await user.click(await screen.findByRole('button', { name: 'Account menu for Test Employee' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('stays signed in and says so when the server cannot be reached', async () => {
    mockSignedIn(EMPLOYEE, { 'POST /auth/logout': new TypeError('Failed to fetch') })
    const user = userEvent.setup()
    renderApp()

    await user.click(await screen.findByRole('button', { name: 'Account menu for Test Employee' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not sign out')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Welcome')
  })

  it('closes the account menu with Escape and returns focus', async () => {
    mockSignedIn(EMPLOYEE)
    const user = userEvent.setup()
    renderApp()

    const button = await screen.findByRole('button', { name: 'Account menu for Test Employee' })
    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('test.employee')).toBeInTheDocument()
    expect(screen.getByText('Employee')).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button).toHaveFocus()
  })
})

describe('expired sessions', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns to sign-in with a message when an API call reports 401', async () => {
    mockSignedIn(HR_ADMIN, { 'GET /admin/users': reply(errorBody('unauthenticated'), 401) })
    const { router } = renderApp('/admin/users')

    expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.state).toEqual({ from: '/admin/users' })
  })

  it('re-checks the session when it is due to expire', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const api = mockApi({
      'GET /auth/session': reply(sessionBody(EMPLOYEE, { idleMs: 60_000 })),
    })
    renderApp()
    await screen.findByRole('button', { name: 'Account menu for Test Employee' })
    const checksBefore = api.requestsTo('GET /auth/session').length

    api.setRoute('GET /auth/session', reply(ANONYMOUS_SESSION))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(66_000)
    })

    expect(await screen.findByText('Your session has ended. Please sign in again.')).toBeInTheDocument()
    expect(api.requestsTo('GET /auth/session').length).toBe(checksBefore + 1)
  })

  it('keeps the user signed in when the server extended the session', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const api = mockApi({
      'GET /auth/session': reply(sessionBody(EMPLOYEE, { idleMs: 60_000 })),
    })
    renderApp()
    await screen.findByRole('button', { name: 'Account menu for Test Employee' })

    api.setRoute('GET /auth/session', () => reply(sessionBody(EMPLOYEE, { idleMs: 30 * 60_000 })))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(66_000)
    })

    expect(screen.getByRole('button', { name: 'Account menu for Test Employee' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Sign in' })).not.toBeInTheDocument()
  })
})

describe('change password', () => {
  it('holds users who must change their password on the change-password page', async () => {
    mockSignedIn(makeUser({ password_must_change: true }))
    const { router } = renderApp('/admin/users')

    expect(await screen.findByRole('heading', { name: 'Change password' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/change-password')
    expect(screen.getByText('You must change your password before you can continue.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
  })

  it('checks required fields and matching confirmation locally', async () => {
    const api = mockSignedIn(EMPLOYEE)
    const user = userEvent.setup()
    renderApp('/change-password')

    await user.click(await screen.findByRole('button', { name: 'Change password' }))
    expect(screen.getByText('Enter your current password.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Current password'), 'old-Password-1')
    await user.type(screen.getByLabelText('New password'), 'new-Password-22')
    await user.type(screen.getByLabelText('Confirm new password'), 'new-Password-23')
    await user.click(screen.getByRole('button', { name: 'Change password' }))
    expect(screen.getByText('The new passwords do not match.')).toBeInTheDocument()
    expect(api.requestsTo('POST /auth/password')).toHaveLength(0)
  })

  async function submitChange(user: ReturnType<typeof userEvent.setup>) {
    await user.type(await screen.findByLabelText('Current password'), 'old-Password-1')
    await user.type(screen.getByLabelText('New password'), 'new-Password-22')
    await user.type(screen.getByLabelText('Confirm new password'), 'new-Password-22')
    await user.click(screen.getByRole('button', { name: 'Change password' }))
  }

  it('translates each password-policy issue returned by the server', async () => {
    mockSignedIn(EMPLOYEE, {
      'POST /auth/password': reply(
        errorBody('password_policy', 'Policy', [
          { location: ['body', 'new_password'], message: 'too_short', type: 'too_short' },
          { location: ['body', 'new_password'], message: 'too_common', type: 'too_common' },
          { location: ['body', 'new_password'], message: 'x', type: 'brand_new_rule' },
        ]),
        422,
      ),
    })
    const user = userEvent.setup()
    renderApp('/change-password')

    await submitChange(user)

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText('It is too short.')).toBeInTheDocument()
    expect(within(alert).getByText(/It is too common/)).toBeInTheDocument()
    expect(within(alert).getByText('It does not meet the password policy.')).toBeInTheDocument()
    expect(screen.getByLabelText('New password')).toHaveValue('')
  })

  it('marks a wrong current password on its field', async () => {
    mockSignedIn(EMPLOYEE, {
      'POST /auth/password': reply(errorBody('invalid_current_password'), 400),
    })
    const user = userEvent.setup()
    renderApp('/change-password')

    await submitChange(user)
    expect(await screen.findByText('The current password is incorrect.')).toBeInTheDocument()
    expect(screen.getByLabelText('Current password')).toHaveAttribute('aria-invalid', 'true')
  })

  it('changes the password, rotates the CSRF token and releases a forced change', async () => {
    const forced = makeUser({ password_must_change: true })
    const api = mockSignedIn(forced, {
      'POST /auth/password': reply(sessionBody(EMPLOYEE, { csrfToken: 'rotated-token' })),
      'POST /auth/logout': reply(undefined, 204),
    })
    const user = userEvent.setup()
    renderApp('/change-password')

    await submitChange(user)

    expect(await screen.findByText('Password changed')).toBeInTheDocument()
    const [change] = api.requestsTo('POST /auth/password')
    expect(change.body).toEqual({ current_password: 'old-Password-1', new_password: 'new-Password-22' })
    expect(change.headers[CSRF]).toBe('csrf-test-token-1')

    await user.click(screen.getByRole('link', { name: 'Continue to dashboard' }))
    await user.click(await screen.findByRole('button', { name: 'Account menu for Test Employee' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    await screen.findByRole('heading', { name: 'Sign in' })
    expect(api.requestsTo('POST /auth/logout')[0].headers[CSRF]).toBe('rotated-token')
  })

  it('is reachable from the account menu', async () => {
    mockSignedIn(EMPLOYEE)
    const user = userEvent.setup()
    const { router } = renderApp()

    await user.click(await screen.findByRole('button', { name: 'Account menu for Test Employee' }))
    await user.click(screen.getByRole('link', { name: 'Change password' }))
    expect(await screen.findByRole('heading', { name: 'Change password' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/change-password')
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toBeInTheDocument()
  })
})

describe('security properties', () => {
  it('keeps passwords and session tokens out of storage and logs', async () => {
    const consoleSpies = (['log', 'info', 'warn', 'error', 'debug'] as const).map((method) =>
      vi.spyOn(console, method),
    )
    mockApi({
      'POST /auth/login': reply(sessionBody(HR_ADMIN, { csrfToken: 'secret-csrf-value' })),
      'POST /auth/logout': reply(undefined, 204),
    })
    const user = userEvent.setup()
    renderApp('/login')

    await fillLogin(user, 'test.hradmin', PASSWORD)
    await user.click(await screen.findByRole('button', { name: 'Account menu for Test HR Admin' }))
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    await screen.findByRole('heading', { name: 'Sign in' })

    const storage = JSON.stringify({ ...window.localStorage }) + JSON.stringify({ ...window.sessionStorage })
    expect(storage).not.toContain(PASSWORD)
    expect(storage).not.toContain('secret-csrf-value')
    expect(Object.keys(window.sessionStorage)).toHaveLength(0)
    expect(Object.keys(window.localStorage).every((key) => key === 'lms.language')).toBe(true)

    const logged = JSON.stringify(consoleSpies.flatMap((spy) => spy.mock.calls))
    expect(logged).not.toContain(PASSWORD)
    expect(logged).not.toContain('secret-csrf-value')
  })

  it('never caches the CSRF token or unknown fields with the session', async () => {
    mockApi({
      'GET /auth/session': reply({
        ...sessionBody(EMPLOYEE, { csrfToken: 'cached-csrf?' }),
        user: { ...EMPLOYEE, password_hash: '$argon2id$should-not-appear' },
      }),
    })
    const { queryClient } = renderApp()
    await screen.findByRole('button', { name: 'Account menu for Test Employee' })

    const cached = JSON.stringify(queryClient.getQueryData(['auth', 'session']))
    expect(cached).not.toContain('cached-csrf?')
    expect(cached).not.toContain('password_hash')
    expect(cached).not.toContain('argon2')
  })
})
