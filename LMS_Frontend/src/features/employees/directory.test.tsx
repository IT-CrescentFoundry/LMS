import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { changeLanguage } from '../../i18n'
import { ACTIVE, employeeRoutes, SEPARATED, summary, UNKNOWN } from '../../test/employeeFixtures'
import { page } from '../../test/orgFixtures'
import {
  EMPLOYEE,
  errorBody,
  HR_ADMIN,
  makeUser,
  mockSignedIn,
  renderApp,
  reply,
  SUPERVISOR,
} from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

async function findTable() {
  return screen.findByRole('table', { name: 'Employees' })
}

describe('Employee directory', () => {
  it('lists employees with code, status, primary unit path and manager', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees')

    const table = await findTable()
    expect(screen.getByRole('heading', { level: 1, name: 'Employees' })).toBeInTheDocument()
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(3)
    const first = rows[0]
    expect(within(first).getByRole('link', { name: '00042 · Test Person One' })).toHaveAttribute(
      'href',
      '/employees/emp-1',
    )
    expect(first).toHaveTextContent('Operation')
    expect(first).toHaveTextContent('Test Melting')
    expect(within(first).getByRole('link', { name: 'T-MGR · Test Manager' })).toBeInTheDocument()
    expect(screen.getByText('Showing 3 employees')).toBeInTheDocument()
  })

  it('never shows an unrecorded status as active', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees')

    const table = await findTable()
    const [active, unknown, separated] = within(table).getAllByRole('row').slice(1)
    const badge = (row: HTMLElement) => row.querySelector('[data-status]')
    expect(badge(active)).toHaveAttribute('data-status', 'active')
    expect(badge(active)).toHaveTextContent('Active')
    expect(badge(unknown)).toHaveAttribute('data-status', 'unknown')
    expect(badge(unknown)).toHaveTextContent('Not recorded')
    expect(badge(unknown)).not.toHaveTextContent('Active')
    expect(badge(unknown)?.className).not.toContain('emerald')
    expect(badge(separated)).toHaveTextContent('Separated')
    expect(unknown).toHaveTextContent('No primary assignment')
  })

  it('applies every filter with the API parameter names and keeps them in the URL', async () => {
    const api = mockSignedIn(HR_ADMIN, employeeRoutes())
    const user = userEvent.setup()
    const { router } = renderApp('/employees')
    await findTable()

    await user.type(screen.getByRole('searchbox', { name: 'Search' }), ' 0004 ')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Employment status' }), 'unknown')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Login account' }), 'no')
    const unit = await screen.findByRole('combobox', { name: 'Organisation unit' })
    await waitFor(() => expect(within(unit).getAllByRole('option').length).toBeGreaterThan(1))
    await user.selectOptions(unit, 'Operation › Test Melting (TEST_MELT)')
    await user.click(screen.getByRole('checkbox', { name: 'Include units below it' }))
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Designation' }), 'des-1')
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Location' }), 'loc-1')
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => expect(api.requestsTo('GET /employees')).toHaveLength(2))
    const last = api.requestsTo('GET /employees').at(-1)
    expect(Object.fromEntries(last?.query ?? [])).toEqual({
      q: '0004',
      status: 'unknown',
      has_account: 'false',
      unit: 'unit-melt',
      include_descendants: 'false',
      designation: 'des-1',
      location: 'loc-1',
      limit: '50',
    })
    expect(router.state.location.search).toBe(
      '?q=0004&status=unknown&unit=unit-melt&sub=0&location=loc-1&designation=des-1&account=no',
    )

    await user.click(screen.getByRole('button', { name: 'Reset' }))
    await waitFor(() => expect(router.state.location.search).toBe(''))
  })

  it('restores filters from the URL (back navigation) and shows the as-of date', async () => {
    const api = mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees?status=separated&as_of=2026-02-01')

    await findTable()
    expect(Object.fromEntries(api.requestsTo('GET /employees')[0].query)).toEqual({
      status: 'separated',
      as_of: '2026-02-01',
      limit: '50',
    })
    expect(screen.getByRole('combobox', { name: 'Employment status' })).toHaveValue('separated')
    expect(screen.getByText(/Organisational context shown as of/)).toBeInTheDocument()
  })

  it('loads more with the cursor', async () => {
    const api = mockSignedIn(HR_ADMIN, employeeRoutes())
    api.setRoute('GET /employees', (request) =>
      request.query.get('cursor') === 'next'
        ? reply({ items: [SEPARATED], next_cursor: null })
        : reply({ items: [ACTIVE, UNKNOWN], next_cursor: 'next' }),
    )
    const user = userEvent.setup()
    renderApp('/employees')
    await findTable()

    await user.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByText('Showing 3 employees')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes({ 'GET /employees': page([]) }))
    renderApp('/employees')
    expect(await screen.findByText('No employees match these filters.')).toBeInTheDocument()
  })

  it('shows the translated reason when the list cannot be loaded', async () => {
    mockSignedIn(HR_ADMIN, employeeRoutes({ 'GET /employees': reply(errorBody('invalid_cursor'), 422) }))
    renderApp('/employees')
    expect(await screen.findByText('Could not load employees.')).toBeInTheDocument()
    expect(screen.getByText('The list position is no longer valid. Reload the list.')).toBeInTheDocument()
  })

  it('is hidden from users without employees.view', async () => {
    mockSignedIn(SUPERVISOR, employeeRoutes())
    renderApp('/employees')

    expect(await screen.findByRole('heading', { name: /do not have access/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Employees' })).not.toBeInTheDocument()

    vi.unstubAllGlobals()
    mockSignedIn(EMPLOYEE, employeeRoutes())
    renderApp('/')
    await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(screen.queryByRole('link', { name: 'Employees' })).not.toBeInTheDocument()
  })

  it('shows the navigation entry and a read-only header for view-only users', async () => {
    const viewer = makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW] })
    mockSignedIn(viewer, employeeRoutes())
    renderApp('/employees')

    await findTable()
    expect(screen.getByRole('link', { name: 'Employees' })).toHaveAttribute('href', '/employees')
    expect(screen.getByText('Read only')).toBeInTheDocument()
    // Without organisation.view the reference-data filters are not offered (no 403 calls).
    expect(screen.queryByRole('combobox', { name: 'Organisation unit' })).not.toBeInTheDocument()
  })

  it('stacks rows into labelled cards on narrow screens', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }))
    mockSignedIn(HR_ADMIN, employeeRoutes({ 'GET /employees': page([summary('emp-9', 'T-9', 'Test Nine')]) }))
    renderApp('/employees')

    const table = await findTable()
    const row = within(table).getAllByRole('row')[1]
    // Each cell carries its column label for the stacked (card) layout.
    expect(within(row).getByText('Primary unit')).toBeInTheDocument()
    expect(within(row).getByText('Line manager')).toBeInTheDocument()
  })

  it('is translated (Hindi)', async () => {
    await changeLanguage('hi')
    mockSignedIn(HR_ADMIN, employeeRoutes())
    renderApp('/employees')

    expect(await screen.findByRole('table', { name: 'कर्मचारी' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'कर्मचारी' })).toBeInTheDocument()
    expect(screen.getAllByText('दर्ज नहीं').length).toBeGreaterThan(0)
  })
})
