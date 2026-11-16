import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { employeeRef, ME, REPORTING, reportingRecord, writeRoutes } from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const NEW_MANAGER = employeeRef('emp-2', 'T-0002', 'Test Person Two', null)

async function openTab(routes = writeRoutes()) {
  const api = mockSignedIn(HR_ADMIN, routes)
  const user = userEvent.setup()
  renderApp('/employees/emp-1/reporting')
  await screen.findByRole('table', { name: 'Reporting history' })
  return { api, user }
}

async function chooseManager(user: ReturnType<typeof userEvent.setup>, buttonName: string) {
  await user.click(screen.getByRole('button', { name: buttonName }))
  const dialog = await screen.findByRole('dialog')
  await within(dialog).findByRole('option', { name: /^T-0002 · Test Person Two/ })
  await user.selectOptions(within(dialog).getByLabelText(/^Line manager/), 'emp-2')
  await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
  return dialog
}

describe('Reporting relationships', () => {
  it('shows the manager, direct reports and history; being a manager grants no access', async () => {
    await openTab()
    expect(screen.getByText('Being a manager in a reporting line grants no access rights.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'T-SUB · Test Subordinate' })).toBeInTheDocument()
    const history = within(screen.getByRole('table', { name: 'Reporting history' })).getAllByRole('row').slice(1)
    // Only the open line can be ended.
    expect(within(history[0]).queryByRole('button', { name: /^End/ })).not.toBeInTheDocument()
    expect(within(history[1]).getByRole('button', { name: 'End Test Manager' })).toBeInTheDocument()
  })

  it('replaces the current manager from a date; the type is left to the server (LINE_MANAGER)', async () => {
    const created = reportingRecord('rep-9', ME, NEW_MANAGER, '2026-12-01', null)
    const { api, user } = await openTab(writeRoutes({ 'POST /employees/emp-1/reporting': reply(created, 201) }))
    const dialog = await chooseManager(user, 'Change line manager')
    expect(dialog).toHaveTextContent('Current line manager: T-MGR · Test Manager')
    expect(dialog).toHaveTextContent('This replaces the current line manager from this date')
    // The employee being edited is never offered as their own manager.
    expect(within(dialog).queryByRole('option', { name: /^00042/ })).not.toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Save line manager' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/reporting')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/reporting')[0].body).toEqual({
      manager_id: 'emp-2',
      effective_from: '2026-12-01',
      reason: null,
    })
    expect(await screen.findByText(/Line manager set to T-0002 · Test Person Two/)).toBeInTheDocument()
  })

  it('sets a first line manager when there is none', async () => {
    const { user } = await openTab(
      writeRoutes({ 'GET /employees/emp-1/reporting': reply({ ...REPORTING, managers: [], history: [] }) }),
    )
    const dialog = await chooseManager(user, 'Set line manager')
    expect(dialog).not.toHaveTextContent('Current line manager')
  })

  it.each([
    ['self_reporting', 422, 'An employee cannot report to themselves.'],
    ['reporting_cycle', 409, 'This manager reports, directly or indirectly, to the employee.'],
    ['manager_separated', 422, 'The selected manager has separated.'],
    ['later_change_exists', 409, 'A later change already exists. End or correct it first.'],
    ['outside_employment_period', 422, "The dates fall outside the employee's employment period."],
  ])('translates %s', async (code, status, text) => {
    const { api, user } = await openTab(writeRoutes({ 'POST /employees/emp-1/reporting': reply(errorBody(code), status) }))
    const dialog = await chooseManager(user, 'Change line manager')
    await user.click(within(dialog).getByRole('button', { name: 'Save line manager' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(text)
    expect(api.requestsTo('POST /employees/emp-1/reporting')).toHaveLength(1) // never retried
  })

  it('ends a reporting line with the exclusive end', async () => {
    const { api, user } = await openTab(
      writeRoutes({
        'POST /employees/emp-1/reporting/rep-2/end': reply({ ...REPORTING.history[1], effective_to: '2027-01-01' }),
      }),
    )
    await user.click(screen.getByRole('button', { name: 'End Test Manager' }))
    const dialog = await screen.findByRole('dialog', { name: 'End reporting line to Test Manager' })
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-12-31')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm end date' }))
    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/reporting/rep-2/end')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/reporting/rep-2/end')[0].body).toEqual({
      effective_to: '2027-01-01',
      reason: null,
    })
  })

  it('needs reporting_lines.manage (employees.manage alone is not enough)', async () => {
    const hrWithoutReporting = makeUser({
      permissions: [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_HISTORY_VIEW, PERMISSIONS.EMPLOYEES_MANAGE],
    })
    mockSignedIn(hrWithoutReporting, writeRoutes())
    renderApp('/employees/emp-1/reporting')
    await screen.findByRole('table', { name: 'Reporting history' })
    expect(screen.queryByRole('button', { name: /line manager$/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^End/ })).not.toBeInTheDocument()
  })
})
