import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DATA_QUALITY_CHECKS } from '../../types/employee'
import { SEPARATED, UNKNOWN, writeRoutes } from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply, type RecordedRequest } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const COUNTS = {
  unknown_status: 1,
  no_primary_assignment: 1,
  missing_location: 0,
  missing_designation: 0,
  separated_with_active_account: 2,
  manager_inactive: 0,
  no_line_manager: 4,
  incomplete_record: 0,
}

function report(request: RecordedRequest) {
  const check = request.query.get('check')
  const cursor = request.query.get('cursor')
  const items =
    check === 'separated_with_active_account'
      ? cursor
        ? [{ ...SEPARATED, public_id: 'emp-4', employee_code: 'T-0004' }]
        : [SEPARATED]
      : check === 'unknown_status'
        ? [UNKNOWN]
        : []
  return reply({
    as_of: request.query.get('as_of') ?? '2026-11-14',
    counts: COUNTS,
    check,
    items,
    next_cursor: check === 'separated_with_active_account' && !cursor ? 'T-0003' : null,
  })
}

function setup(user = HR_ADMIN) {
  const api = mockSignedIn(user, writeRoutes({ 'GET /employees/data-quality': report }))
  return api
}

describe('Data quality', () => {
  it('shows the eight checks with their counts and descriptions from the server', async () => {
    setup()
    renderApp('/employees/data-quality')
    expect(await screen.findByRole('heading', { level: 1, name: 'Data quality' })).toBeInTheDocument()
    const checks = within(await screen.findByRole('region', { name: /^Checks on/ })).getAllByRole('button')
    expect(checks).toHaveLength(8)
    expect(checks.map((button) => button.getAttribute('data-check'))).toEqual([...DATA_QUALITY_CHECKS])
    const noManager = checks.find((button) => button.getAttribute('data-check') === 'no_line_manager')!
    expect(noManager).toHaveTextContent('No line manager')
    expect(noManager).toHaveTextContent('A current employee without a line manager on this date.')
    expect(within(noManager).getByText('4')).toBeInTheDocument()
    expect(screen.getByText('Choose a check to see the employees it lists.')).toBeInTheDocument()
    expect(screen.getByText(/This page only reports/)).toBeInTheDocument()
  })

  it('lists one check, pages it and links each employee to where it is corrected', async () => {
    const api = setup()
    const user = userEvent.setup()
    const { router } = renderApp('/employees/data-quality?as_of=2026-11-01')
    await user.click(await screen.findByRole('button', { name: /^Separated with an active account/ }))

    await waitFor(() => expect(router.state.location.search).toContain('check=separated_with_active_account'))
    const list = await screen.findByRole('table', { name: 'Separated with an active account' })
    expect(screen.getByRole('heading', { name: 'Separated with an active account: 2 employees' })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: 'Review T-0003' })).toHaveAttribute(
      'href',
      '/employees/emp-3/account?as_of=2026-11-01',
    )
    const last = api.requestsTo('GET /employees/data-quality').at(-1)!
    expect(Object.fromEntries(last.query)).toEqual({ as_of: '2026-11-01', check: 'separated_with_active_account', limit: '50' })

    await user.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await within(list).findByRole('link', { name: 'Review T-0004' })).toBeInTheDocument()
    expect(api.requestsTo('GET /employees/data-quality').at(-1)!.query.get('cursor')).toBe('T-0003')
    // Strictly read-only: only GET requests were sent.
    expect(api.requests.filter((r) => r.method !== 'GET')).toHaveLength(0)
  })

  it('never shows the previous list (or "no issues") while another check loads', async () => {
    let release: () => void = () => {}
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    mockSignedIn(
      HR_ADMIN,
      writeRoutes({
        'GET /employees/data-quality': async (request) => {
          if (request.query.get('check') === 'unknown_status') await held
          return report(request)
        },
      }),
    )
    const user = userEvent.setup()
    renderApp('/employees/data-quality?check=missing_location')
    expect(await screen.findByText('No employee fails this check on this date.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^Status not recorded/ }))

    const list = await screen.findByRole('region', { name: /^Status not recorded/ })
    expect(list).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByText('No employee fails this check on this date.')).not.toBeInTheDocument()
    expect(within(list).queryByRole('table')).not.toBeInTheDocument()
    // The counts stay visible meanwhile.
    expect(screen.getAllByRole('button', { pressed: true })).toHaveLength(1)

    release()
    expect(await within(list).findByRole('link', { name: 'Review T-0002' })).toBeInTheDocument()
    expect(list).toHaveAttribute('aria-busy', 'false')
  })

  it('shows an empty state for a check without issues', async () => {
    setup()
    const user = userEvent.setup()
    renderApp('/employees/data-quality')
    await user.click(await screen.findByRole('button', { name: /^Location missing/ }))
    expect(await screen.findByText('No employee fails this check on this date.')).toBeInTheDocument()
  })

  it('links status problems to the overview and keeps the check in the URL', async () => {
    setup()
    renderApp('/employees/data-quality?check=unknown_status')
    const list = await screen.findByRole('table', { name: 'Status not recorded' })
    expect(within(list).getByRole('link', { name: 'Review T-0002' })).toHaveAttribute('href', '/employees/emp-2')
    expect(screen.getByRole('button', { name: /^Status not recorded/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows a translated error when the report cannot be loaded', async () => {
    mockSignedIn(HR_ADMIN, writeRoutes({ 'GET /employees/data-quality': reply(errorBody('invalid_check'), 422) }))
    renderApp('/employees/data-quality')
    expect(await screen.findByText('Could not load the data-quality report.')).toBeInTheDocument()
  })

  it('offers the section only with employees.manage; the URL shows the forbidden page otherwise', async () => {
    const viewer = makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_HISTORY_VIEW] })
    const api = setup(viewer)
    renderApp('/employees')
    await screen.findByRole('heading', { level: 1, name: 'Employees' })
    expect(screen.queryByRole('navigation', { name: 'Employee area' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Data quality' })).not.toBeInTheDocument()
    vi.unstubAllGlobals()

    setup(viewer)
    renderApp('/employees/data-quality')
    expect(await screen.findByText('You do not have access to this page')).toBeInTheDocument()
    expect(api.requestsTo('GET /employees/data-quality')).toHaveLength(0)
  })

  it('shows Directory and Data quality pills to HR Admin', async () => {
    setup()
    const user = userEvent.setup()
    renderApp('/employees')
    const nav = await screen.findByRole('navigation', { name: 'Employee area' })
    expect(within(nav).getByRole('link', { name: 'Directory' })).toHaveAttribute('aria-current', 'page')
    await user.click(within(nav).getByRole('link', { name: 'Data quality' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Data quality' })).toBeInTheDocument()
  })
})
