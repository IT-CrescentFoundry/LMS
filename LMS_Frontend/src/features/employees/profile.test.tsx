import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { changeLanguage } from '../../i18n'
import { formatDate } from '../../lib/format'
import { employee, employeeRoutes, UNKNOWN } from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const d = (iso: string) => formatDate(iso, 'en')
const VIEWER = makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW] })

function tabs(label = 'Employee sections') {
  return within(screen.getByRole('navigation', { name: label }))
    .getAllByRole('link')
    .map((link) => link.textContent)
}

describe('Employee profile', () => {
  it('shows the header, overview and the position as computed by the server', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1')

    expect(await screen.findByRole('heading', { level: 1, name: 'Test Person One' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Employees00042')
    expect(tabs()).toEqual([
      'Overview',
      'Assignments',
      'Functional roles',
      'Responsibilities',
      'Reporting',
      'Login account',
      'History',
    ])
    expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute('aria-current', 'page')
    const position = screen.getByRole('region', { name: `Position on ${d('2026-11-14')}` })
    // The path comes from the API (no client-side reconstruction from the tree).
    expect(position).toHaveTextContent('Operation')
    expect(position).toHaveTextContent('Test Melting')
    expect(within(position).getByRole('link', { name: 'T-MGR · Test Manager' })).toBeInTheDocument()
    const details = screen.getByRole('region', { name: 'Employee details' })
    expect(details).toHaveTextContent('00042')
    expect(details).toHaveTextContent('हिन्दी')
    expect(details).toHaveTextContent('person.one@example.test')
  })

  it('passes the as-of date to the API and keeps it in every tab link', async () => {
    const api = mockSignedIn(HR_ADMIN, employeeRoutes())
    const user = userEvent.setup()
    const { router } = renderApp('/employees/emp-1/roles?as_of=2026-02-01')

    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })
    await screen.findByRole('table', { name: 'Functional roles' })
    expect(Object.fromEntries(api.requestsTo('GET /employees/emp-1')[0].query)).toEqual({ as_of: '2026-02-01' })
    expect(api.requestsTo('GET /employees/emp-1/functional-roles')[0].query.get('as_of')).toBe('2026-02-01')
    expect(screen.getByRole('link', { name: 'Reporting' })).toHaveAttribute(
      'href',
      '/employees/emp-1/reporting?as_of=2026-02-01',
    )

    await user.click(screen.getByRole('button', { name: 'Today' }))
    await waitFor(() => expect(router.state.location.search).toBe(''))
  })

  it('shows an unrecorded status as "Not recorded", never as active', async () => {
    mockSignedIn(
      HR_ADMIN,
      employeeRoutes({ 'GET /employees/emp-1': reply(employee(UNKNOWN, { public_id: 'emp-1' })) }),
    )
    renderApp('/employees/emp-1')

    await screen.findByRole('heading', { level: 1, name: 'Test Person Two' })
    const badges = [...document.querySelectorAll('[data-status]')]
    expect(badges.map((badge) => badge.getAttribute('data-status'))).not.toContain('active')
    expect(badges[0]).toHaveTextContent('Not recorded')
    expect(screen.getByRole('region', { name: `Position on ${d('2026-11-14')}` })).toHaveTextContent(
      'No primary assignment',
    )
  })

  it('shows the assignment timeline with the last day in effect', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/assignments')

    const table = await screen.findByRole('table', { name: 'Assignment timeline' })
    const [first, second] = within(table).getAllByRole('row').slice(1)
    // effective_to 2026-07-01 is exclusive: the last day in effect is 30 June.
    expect(first).toHaveTextContent(`From ${d('2025-04-01')} · last day ${d('2026-06-30')}`)
    expect(first).toHaveTextContent('Operation')
    expect(second).toHaveTextContent(`From ${d('2026-07-01')} · ongoing`)
    expect(second).toHaveTextContent('Test Grade One')
    expect(screen.getByRole('checkbox', { name: 'Include ended records' })).toBeChecked()
  })

  it('presents derived, manual and excluded functional roles', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/roles')

    const table = await screen.findByRole('table', { name: 'Functional roles' })
    const rows = within(table).getAllByRole('row').slice(1)
    const byRole = (name: string) => rows.find((row) => row.textContent?.includes(name)) as HTMLElement
    expect(byRole('Test Melting Work')).toHaveTextContent('In effect')
    expect(byRole('Test Melting Work')).toHaveTextContent(
      'From designation Test Operator in Test Melting (Primary assignment)',
    )
    expect(byRole('Test Internal Audit')).toHaveTextContent('Assigned manually')
    expect(byRole('Test Safety Duty')).toHaveTextContent('Not in effect (excluded)')
    expect(byRole('Test Safety Duty')).toHaveTextContent('Excluded — Medical restriction')
    expect(screen.getByText(/never grant LMS permissions/)).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Manual roles and exclusions' })).toHaveTextContent('Exclusion')
  })

  it('shows responsibilities with their context', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/responsibilities')

    const table = await screen.findByRole('table', { name: 'Responsibilities' })
    expect(table).toHaveTextContent('Test Fire Warden')
    expect(table).toHaveTextContent('Unit: Operation')
  })

  it('shows managers, direct reports and the reporting history', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/reporting')

    const managers = await screen.findByRole('region', { name: `Reports to (on ${d('2026-11-14')})` })
    expect(within(managers).getByRole('link', { name: 'T-MGR · Test Manager' })).toBeInTheDocument()
    const reports = screen.getByRole('region', { name: `Direct reports (on ${d('2026-11-14')})` })
    expect(within(reports).getByRole('link', { name: 'T-SUB · Test Subordinate' })).toBeInTheDocument()
    expect(reports).toHaveTextContent('Not recorded')
    const history = screen.getByRole('table', { name: 'Reporting history' })
    expect(within(history).getAllByRole('row')).toHaveLength(3)
    expect(history).toHaveTextContent(`last day ${d('2026-06-30')}`)
    expect(screen.getByText(/grants no access rights/)).toBeInTheDocument()
  })

  it('shows linked accounts, flags and link history without network details', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/account')

    const table = await screen.findByRole('table', { name: 'Linked accounts' })
    expect(table).toHaveTextContent('test.one')
    expect(table).toHaveTextContent('Disabled')
    expect(screen.getByText('The work email differs from the email of a linked account.')).toBeInTheDocument()
    expect(screen.getByText('Disabled accounts keep their link as history.')).toBeInTheDocument()
    const history = screen.getByRole('region', { name: 'Link history' })
    expect(history).toHaveTextContent('Login account linked')
    expect(history).toHaveTextContent('By HR Tester (hr.tester)')
    expect(history).toHaveTextContent('Reason: New login')
    expect(document.body).not.toHaveTextContent('127.0.0.1')
    // HR Admin holds employees.manage + user_accounts.manage + user_accounts.view (CP4).
    expect(screen.getByRole('button', { name: 'Link login account' })).toBeInTheDocument()
    expect(within(table).getByRole('button', { name: 'Unlink test.one' })).toBeInTheDocument()
  })

  it('shows the change history with translated event types', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1/history')

    expect(await screen.findByText('Assignment changed from a date')).toBeInTheDocument()
    const list = screen.getByRole('region', { name: 'Change history' })
    expect(list).toHaveTextContent('Employee record created')
    expect(list).toHaveTextContent('Reason: Transfer')
    expect(screen.getByText('Showing 2 changes')).toBeInTheDocument()
  })

  it('hides the assignment and history tabs without employees.history.view', async () => {
    mockSignedIn(VIEWER, employeeRoutes())
    renderApp('/employees/emp-1')

    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })
    expect(tabs()).toEqual(['Overview', 'Functional roles', 'Responsibilities', 'Reporting', 'Login account'])
    expect(screen.getByText('Read only')).toBeInTheDocument()
  })

  it.each(['assignments', 'history'])('refuses the %s tab URL without employees.history.view', async (tab) => {
    const api = mockSignedIn(VIEWER, employeeRoutes())
    renderApp(`/employees/emp-1/${tab}`)

    expect(await screen.findByRole('heading', { name: /do not have access/i })).toBeInTheDocument()
    expect(api.requestsTo(`GET /employees/emp-1/${tab}`)).toHaveLength(0)
  })

  it('explains a missing employee', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes({ 'GET /employees/emp-1': reply(errorBody('employee_not_found'), 404) }))
    renderApp('/employees/emp-1')

    expect(await screen.findByText('Could not load this employee.')).toBeInTheDocument()
    expect(screen.getByText('This employee record was not found.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it('makes no write requests while browsing every tab', async () => {
    const api = mockSignedIn(HR_ADMIN, employeeRoutes())
    const user = userEvent.setup()
    renderApp('/employees/emp-1')
    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })

    for (const name of ['Assignments', 'Functional roles', 'Responsibilities', 'Reporting', 'Login account', 'History']) {
      await user.click(screen.getByRole('link', { name }))
      await waitFor(() => expect(screen.getByRole('link', { name })).toHaveAttribute('aria-current', 'page'))
    }
    expect(api.requests.filter((request) => request.method !== 'GET')).toEqual([])
  })

  it('is translated (Gujarati)', async () => {
    await changeLanguage('gu')
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees/emp-1')

    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })
    expect(tabs('કર્મચારી વિભાગો')).toContain('કાર્યાત્મક ભૂમિકાઓ')
    expect(screen.getByRole('region', { name: 'કર્મચારીની વિગતો' })).toBeInTheDocument()
  })
})
