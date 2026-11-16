import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { formatDate } from '../../lib/format'
import {
  DIRECT_REPORTS,
  employee,
  OWN_RECORDS,
  separationPreview,
  writeRoutes,
} from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply, type MockRoute } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const d = (iso: string) => formatDate(iso, 'en')
const PREVIEW = 'GET /employees/emp-1/separation-preview'
const POST = 'POST /employees/emp-1/employment-status'
const SEPARATED = employee(undefined, { employment_status: 'separated', date_of_separation: '2026-12-31' })

const BOTH = separationPreview({
  own_records: OWN_RECORDS,
  direct_reports: DIRECT_REPORTS,
  requires_end_open_records: true,
  requires_end_direct_reports: true,
})

async function startSeparation(routes: Record<string, MockRoute>) {
  const api = mockSignedIn(HR_ADMIN, writeRoutes(routes))
  const user = userEvent.setup()
  renderApp('/employees/emp-1')
  await user.click(await screen.findByRole('button', { name: 'Separate employee' }))
  const dialog = await screen.findByRole('dialog', { name: 'Separate employee: Test Person One' })
  return { api, user, dialog }
}

async function toImpact(user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement, date = '2026-12-31') {
  await user.type(within(dialog).getByLabelText(/^Last Working Day/), date)
  await user.click(within(dialog).getByRole('button', { name: 'Check impact' }))
  await within(dialog).findByText(/^Last working day /)
}

describe('Separation workflow', () => {
  it('asks for the Last Working Day and explains that records end the next day', async () => {
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(BOTH) })
    const input = within(dialog).getByLabelText(/^Last Working Day/)
    expect(input).toHaveFocus()
    expect(dialog).toHaveTextContent('Step 1 of 3')
    await user.type(input, '2026-12-31')
    expect(dialog).toHaveTextContent(
      `Records end from ${d('2027-01-01')}: the first day after the last working day (end dates are exclusive).`,
    )
    expect(api.requestsTo(PREVIEW)).toHaveLength(0) // nothing is checked before the user asks
  })

  it('calls the preview with the date unchanged and separates own records from direct reports', async () => {
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(BOTH) })
    await toImpact(user, dialog)

    expect(api.requestsTo(PREVIEW)).toHaveLength(1)
    expect(Object.fromEntries(api.requestsTo(PREVIEW)[0].query)).toEqual({ separation_date: '2026-12-31' })
    const own = within(dialog).getByRole('region', { name: 'This employee’s own records' })
    expect(own).toHaveTextContent('Assignment: Test Melting')
    expect(own).toHaveTextContent('Reports to Test Manager (T-MGR)')
    expect(own).not.toHaveTextContent('Test Subordinate')
    const reports = within(dialog).getByRole('region', { name: 'Direct reports (this employee is their manager)' })
    expect(reports).toHaveTextContent('T-SUB · Test Subordinate')
    expect(reports).not.toHaveTextContent('Test Melting')
  })

  it('needs both independent confirmations; neither is pre-ticked', async () => {
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(BOTH) })
    await toImpact(user, dialog)
    const endOwn = within(dialog).getByRole('checkbox', { name: /^End these 2 records from/ })
    const endReports = within(dialog).getByRole('checkbox', { name: /^End the reporting line of this 1 employee/ })
    const next = within(dialog).getByRole('button', { name: 'Continue' })
    expect(endOwn).not.toBeChecked()
    expect(endReports).not.toBeChecked()
    expect(next).toBeDisabled()

    await user.click(endOwn)
    expect(endReports).not.toBeChecked() // independent
    expect(next).toBeDisabled()
    await user.click(endOwn)
    await user.click(endReports)
    expect(endOwn).not.toBeChecked()
    expect(next).toBeDisabled()
    await user.click(endOwn)
    expect(next).toBeEnabled()
    expect(api.requestsTo(POST)).toHaveLength(0)
  })

  it('sends the exact payload with both confirmations, the date not converted twice', async () => {
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(BOTH), [POST]: reply(SEPARATED) })
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Resigned')
    await toImpact(user, dialog)
    await user.click(within(dialog).getByRole('checkbox', { name: /^End these 2 records/ }))
    await user.click(within(dialog).getByRole('checkbox', { name: /^End the reporting line/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))

    expect(dialog).toHaveTextContent(`Separate Test Person One (00042) with last working day ${d('2026-12-31')}?`)
    expect(dialog).toHaveTextContent(`2 own records end from ${d('2027-01-01')}.`)
    expect(api.requestsTo(POST)).toHaveLength(0) // nothing is sent before the final confirmation
    await user.click(within(dialog).getByRole('button', { name: 'Confirm separation' }))

    await waitFor(() => expect(api.requestsTo(POST)).toHaveLength(1))
    expect(api.requestsTo(POST)[0].body).toEqual({
      version: 3,
      status: 'separated',
      separation_date: '2026-12-31',
      end_open_records: true,
      end_direct_reports: true,
      reason: 'Resigned',
    })
    expect(await screen.findByText(`The employee was separated. Last working day: ${d('2026-12-31')}.`)).toBeInTheDocument()
  })

  it('sends only end_open_records when there are no direct reports', async () => {
    const ownOnly = separationPreview({ own_records: OWN_RECORDS, requires_end_open_records: true })
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(ownOnly), [POST]: reply(SEPARATED) })
    await toImpact(user, dialog)
    expect(within(dialog).queryByRole('region', { name: /Direct reports/ })).not.toBeInTheDocument()
    await user.click(within(dialog).getByRole('checkbox', { name: /^End these 2 records/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm separation' }))
    await waitFor(() => expect(api.requestsTo(POST)).toHaveLength(1))
    expect(api.requestsTo(POST)[0].body).toMatchObject({ end_open_records: true, end_direct_reports: false })
  })

  it('sends only end_direct_reports when only direct reports continue', async () => {
    const reportsOnly = separationPreview({ direct_reports: DIRECT_REPORTS, requires_end_direct_reports: true })
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(reportsOnly), [POST]: reply(SEPARATED) })
    await toImpact(user, dialog)
    expect(within(dialog).queryByRole('region', { name: /own records/ })).not.toBeInTheDocument()
    await user.click(within(dialog).getByRole('checkbox', { name: /^End the reporting line/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm separation' }))
    await waitFor(() => expect(api.requestsTo(POST)).toHaveLength(1))
    expect(api.requestsTo(POST)[0].body).toMatchObject({ end_open_records: false, end_direct_reports: true })
  })

  it('blocks submission while a record starts after the last working day', async () => {
    const blocked = separationPreview({
      own_records: [{ ...OWN_RECORDS[0], record_id: 'asg-9', effective_from: '2027-02-01', starts_after_separation: true }],
      blocked: true,
    })
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(blocked) })
    await toImpact(user, dialog)
    const section = within(dialog).getByRole('region', { name: 'Cannot be ended automatically' })
    expect(section).toHaveTextContent('Test Melting')
    expect(section).toHaveTextContent('Correct or remove them first')
    expect(within(dialog).getByRole('button', { name: 'Continue' })).toBeDisabled()
    expect(api.requestsTo(POST)).toHaveLength(0)
  })

  it('says when nothing continues and sends no confirmations', async () => {
    const { api, user, dialog } = await startSeparation({ [PREVIEW]: reply(separationPreview()), [POST]: reply(SEPARATED) })
    await toImpact(user, dialog)
    expect(dialog).toHaveTextContent('Nothing continues after this date.')
    expect(within(dialog).queryByRole('checkbox')).not.toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm separation' }))
    await waitFor(() => expect(api.requestsTo(POST)).toHaveLength(1))
    expect(api.requestsTo(POST)[0].body).toMatchObject({
      separation_date: '2026-12-31',
      end_open_records: false,
      end_direct_reports: false,
    })
  })

  it('after a 409 race shows the new blockers, refreshes the preview and never retries', async () => {
    const newReport = { ...DIRECT_REPORTS[0], record_id: 'rep-7', employee: { ...DIRECT_REPORTS[0].employee, employee_code: 'T-NEW', full_name: 'Test New Report' } }
    let previews = 0
    const conflict = errorBody('open_records_on_separation', 'English never shown', [
      { location: ['reporting_line', 'T-NEW'], message: 'x', type: 'open_direct_report' },
    ])
    const { api, user, dialog } = await startSeparation({
      [PREVIEW]: () => {
        previews += 1
        return reply(
          previews === 1
            ? separationPreview({ own_records: OWN_RECORDS, requires_end_open_records: true })
            : separationPreview({
                own_records: OWN_RECORDS,
                direct_reports: [newReport],
                requires_end_open_records: true,
                requires_end_direct_reports: true,
              }),
        )
      },
      [POST]: reply(conflict, 409),
    })
    await toImpact(user, dialog)
    await user.click(within(dialog).getByRole('checkbox', { name: /^End these 2 records/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm separation' }))

    // Back on the impact step with the server's blockers and a refreshed preview.
    expect(await within(dialog).findByText('Direct report T-NEW still reports to this employee')).toBeInTheDocument()
    expect(dialog).toHaveTextContent('The impact below has been refreshed')
    expect(dialog).not.toHaveTextContent('English never shown')
    await within(dialog).findByRole('region', { name: 'Direct reports (this employee is their manager)' })
    expect(api.requestsTo(PREVIEW)).toHaveLength(2)
    // Confirmations must be given again.
    expect(within(dialog).getByRole('checkbox', { name: /^End these 2 records/ })).not.toBeChecked()
    expect(within(dialog).getByRole('button', { name: 'Continue' })).toBeDisabled()
    expect(api.requestsTo(POST)).toHaveLength(1)
  })

  it('is not offered to an already separated employee or without employees.manage', async () => {
    mockSignedIn(HR_ADMIN, writeRoutes({ 'GET /employees/emp-1': reply(SEPARATED) }))
    renderApp('/employees/emp-1')
    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })
    expect(screen.queryByRole('button', { name: 'Separate employee' })).not.toBeInTheDocument()
    vi.unstubAllGlobals()

    mockSignedIn(makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW] }), writeRoutes())
    renderApp('/employees/emp-1')
    await screen.findAllByRole('heading', { level: 1, name: 'Test Person One' })
    expect(screen.queryByRole('button', { name: 'Separate employee' })).not.toBeInTheDocument()
  })
})
