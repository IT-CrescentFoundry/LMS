import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ACCOUNT, writeRoutes } from '../../test/employeeFixtures'
import { page } from '../../test/orgFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply, type MockRoute } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

function account(id: string, login: string, status = 'active', roles = ['employee']) {
  return {
    public_id: id,
    login_id: login,
    display_name: `Synthetic ${login}`,
    email: null,
    status,
    roles,
    last_login_at: null,
    created_at: '2026-11-12T10:00:00Z',
    employee: null,
  }
}

const OWN = account(HR_ADMIN.public_id, HR_ADMIN.login_id, 'active', ['hr_admin'])
const UNLINKED = [account('acc-new', 'synthetic.new'), account('acc-off', 'synthetic.off', 'disabled'), OWN]
const LINKED = { ...ACCOUNT, accounts: [...ACCOUNT.accounts, { public_id: 'acc-new', login_id: 'synthetic.new', display_name: 'New', status: 'active' }] }

async function openLink(routes: Record<string, MockRoute> = {}) {
  const api = mockSignedIn(HR_ADMIN, writeRoutes({ 'GET /admin/users': page(UNLINKED), ...routes }))
  const user = userEvent.setup()
  renderApp('/employees/emp-1/account')
  await user.click(await screen.findByRole('button', { name: 'Link login account' }))
  const dialog = await screen.findByRole('dialog', { name: 'Link a login account: Test Person One' })
  await within(dialog).findByText('synthetic.new')
  return { api, user, dialog }
}

describe('Account linking', () => {
  it('asks the server for unlinked accounts the caller may manage; the own account is never selectable', async () => {
    const { api, user, dialog } = await openLink()
    expect(Object.fromEntries(api.requestsTo('GET /admin/users')[0].query)).toEqual({
      linked: 'false',
      manageable: 'true',
      limit: '25',
    })
    // The server already leaves out the caller's own account; if one is ever listed,
    // the picker still refuses it (defence in depth).
    const radios = within(dialog).getAllByRole('radio')
    expect(radios).toHaveLength(3)
    expect(within(dialog).getByRole('radio', { name: /synthetic\.off/ }).closest('li')).toHaveTextContent('Disabled')
    const own = within(dialog).getByRole('radio', { name: /test\.hradmin/ })
    expect(own).toBeDisabled()
    expect(own.closest('li')).toHaveTextContent('Your account: you cannot link your own account.')
    expect(own.closest('li')).toHaveTextContent('HR Admin')

    await user.type(within(dialog).getByLabelText(/^Find a login account/), 'new')
    await user.click(within(dialog).getByRole('button', { name: 'Search' }))
    await waitFor(() => expect(api.requestsTo('GET /admin/users')).toHaveLength(2))
    expect(Object.fromEntries(api.requestsTo('GET /admin/users')[1].query)).toEqual({
      q: 'new',
      linked: 'false',
      manageable: 'true',
      limit: '25',
    })
  })

  it('searches on Enter without submitting the link form', async () => {
    const { api, user, dialog } = await openLink()
    const search = within(dialog).getByLabelText(/^Find a login account/)
    expect(search).toHaveFocus()
    await user.type(search, 'synthetic{Enter}')
    await waitFor(() => expect(api.requestsTo('GET /admin/users')).toHaveLength(2))
    expect(api.requestsTo('GET /admin/users')[1].query.get('q')).toBe('synthetic')
    expect(within(dialog).queryByText('Choose a login account.')).not.toBeInTheDocument()
    expect(api.requestsTo('PUT /employees/emp-1/account')).toHaveLength(0)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('shows the picker error state when the account list cannot be loaded', async () => {
    mockSignedIn(HR_ADMIN, writeRoutes({ 'GET /admin/users': reply(errorBody('forbidden'), 403) }))
    const user = userEvent.setup()
    renderApp('/employees/emp-1/account')
    await user.click(await screen.findByRole('button', { name: 'Link login account' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('You do not have permission')
  })

  it('links the chosen account with the documented body and nothing else changes', async () => {
    const { api, user, dialog } = await openLink({ 'PUT /employees/emp-1/account': reply(LINKED) })
    await user.click(within(dialog).getByRole('button', { name: 'Link login account' }))
    expect(within(dialog).getByText('Choose a login account.')).toBeInTheDocument()
    await user.click(within(dialog).getByRole('radio', { name: /synthetic\.new/ }))
    await user.type(within(dialog).getByLabelText(/^Reason/), 'New login')
    await user.click(within(dialog).getByRole('button', { name: 'Link login account' }))

    await waitFor(() => expect(api.requestsTo('PUT /employees/emp-1/account')).toHaveLength(1))
    expect(api.requestsTo('PUT /employees/emp-1/account')[0].body).toEqual({
      user_public_id: 'acc-new',
      reason: 'New login',
    })
    expect(await screen.findByText('Login account synthetic.new was linked.')).toBeInTheDocument()
    // No account change of any other kind was requested.
    expect(api.requests.filter((r) => r.method !== 'GET').map((r) => `${r.method} ${r.path}`)).toEqual([
      'PUT /employees/emp-1/account',
    ])
  })

  it.each([
    ['employee_has_active_account', 409, 'This employee already has a linked account that is not disabled.'],
    ['account_already_linked', 409, 'This login account is linked to another employee.'],
    ['insufficient_privilege', 403, 'This account has privileges you do not hold, so you cannot manage it.'],
    ['self_modification_forbidden', 403, 'You cannot perform this action on your own account.'],
  ])('shows %s from the server', async (code, status, text) => {
    const { api, user, dialog } = await openLink({ 'PUT /employees/emp-1/account': reply(errorBody(code), status) })
    await user.click(within(dialog).getByRole('radio', { name: /synthetic\.new/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Link login account' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(text)
    expect(api.requestsTo('PUT /employees/emp-1/account')).toHaveLength(1)
  })

  it('unlinks only after an explicit confirmation', async () => {
    const api = mockSignedIn(HR_ADMIN, writeRoutes({ 'POST /employees/emp-1/account/unlink': reply({ ...ACCOUNT, accounts: [] }) }))
    const user = userEvent.setup()
    renderApp('/employees/emp-1/account')
    await user.click(await screen.findByRole('button', { name: 'Unlink test.one' }))
    const dialog = await screen.findByRole('dialog', { name: 'Unlink test.one' })
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(dialog).toHaveTextContent('Unlink test.one from Test Person One?')
    expect(dialog).toHaveTextContent('The account is not disabled or deleted.')
    expect(api.requestsTo('POST /employees/emp-1/account/unlink')).toHaveLength(0)
    await user.click(within(dialog).getByRole('button', { name: 'Confirm unlink' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/account/unlink')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/account/unlink')[0].body).toEqual({
      user_public_id: 'acc-1',
      reason: null,
    })
  })

  it.each([
    ['employees.manage only', [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_MANAGE, PERMISSIONS.USER_ACCOUNTS_VIEW]],
    ['user_accounts.manage only', [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.USER_ACCOUNTS_MANAGE, PERMISSIONS.USER_ACCOUNTS_VIEW]],
  ])('offers neither link nor unlink with %s', async (_label, permissions) => {
    mockSignedIn(makeUser({ permissions }), writeRoutes())
    renderApp('/employees/emp-1/account')
    await screen.findByRole('table', { name: 'Linked accounts' })
    expect(screen.queryByRole('button', { name: 'Link login account' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Unlink/ })).not.toBeInTheDocument()
  })

  it('offers unlink but not the picker without user_accounts.view', async () => {
    mockSignedIn(
      makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_MANAGE, PERMISSIONS.USER_ACCOUNTS_MANAGE] }),
      writeRoutes(),
    )
    renderApp('/employees/emp-1/account')
    await screen.findByRole('table', { name: 'Linked accounts' })
    expect(screen.queryByRole('button', { name: 'Link login account' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Unlink test.one' })).toBeInTheDocument()
  })
})
